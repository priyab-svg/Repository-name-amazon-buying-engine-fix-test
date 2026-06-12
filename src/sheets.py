import os
import time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

ASIN_COL        = "ASIN"
MARKETPLACE_COL = "Marketplace"
BRAND_COL       = "Brand / Supplier"
TITLE_COL       = "Product Name / Title"
CATEGORY_COL    = "Category"
DESCRIPTION_COL = "Description"
STATUS_COL      = "Current Returnable Status"

OUTPUT_COLS = [
    "Current Returnable Status",
    "Returnable?",
    "Confidence",
    "Classification Reason",
    "Last Checked",
]

WRITE_BATCH_SIZE = 50   # cells per batch_update call
RATE_LIMIT_PAUSE = 3    # seconds between batches
MAX_RETRIES      = 4    # retries on 429


def _get_gspread_client():
    key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    creds = Credentials.from_service_account_file(key_file, scopes=SCOPES)
    return gspread.authorize(creds)


def _batch_update_with_retry(sheet, updates: list):
    """
    Write a list of {range, values} updates in batches.
    Automatically retries with exponential backoff on Google 429 errors.
    """
    batches = [
        updates[i:i + WRITE_BATCH_SIZE]
        for i in range(0, len(updates), WRITE_BATCH_SIZE)
    ]

    for batch_num, batch in enumerate(batches, 1):
        for attempt in range(MAX_RETRIES):
            try:
                sheet.batch_update(batch, value_input_option="USER_ENTERED")
                if len(batches) > 1:
                    print(f"      Batch {batch_num}/{len(batches)} written...")
                if batch_num < len(batches):
                    time.sleep(RATE_LIMIT_PAUSE)
                break
            except gspread.exceptions.APIError as e:
                if "429" in str(e) or "Quota" in str(e):
                    wait = (2 ** attempt) * 10   # 10s, 20s, 40s, 80s
                    print(f"      Rate limit hit — waiting {wait}s before retry...")
                    time.sleep(wait)
                    if attempt == MAX_RETRIES - 1:
                        raise
                else:
                    raise


def read_sheet() -> pd.DataFrame:
    """Read the master ASIN list from Google Sheet via service account."""
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    client = _get_gspread_client()
    sheet = client.open_by_key(sheet_id).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    df[ASIN_COL] = df[ASIN_COL].astype(str).str.strip()
    return df


def get_unclassified(df: pd.DataFrame) -> pd.DataFrame:
    """Return ASINs that are unclassified or previously marked Unknown (to retry with updated rules)."""
    status = df[STATUS_COL].astype(str).str.strip()
    mask = df[STATUS_COL].isna() | (status == "") | (status == "Unknown")
    return df[mask].copy()


def write_results_to_sheet(results: list[dict]):
    """
    Write classification results back to the Google Sheet.
    Matches rows by ASIN, updates output columns only.
    Handles Google Sheets rate limits automatically.
    """
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    client = _get_gspread_client()
    sheet = client.open_by_key(sheet_id).sheet1

    all_values = sheet.get_all_values()
    headers = list(all_values[0])

    if ASIN_COL not in headers:
        raise ValueError(f"'{ASIN_COL}' column not found in sheet.")

    asin_idx = headers.index(ASIN_COL)

    # Add any missing output columns
    for col_name in OUTPUT_COLS:
        if col_name not in headers:
            headers.append(col_name)
            sheet.update_cell(1, len(headers), col_name)
            time.sleep(1)

    result_map = {str(r["ASIN"]).strip(): r for r in results}

    # Build update list — one cell per output column per ASIN
    updates = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        asin = row[asin_idx].strip() if asin_idx < len(row) else ""
        if asin not in result_map:
            continue

        result = result_map[asin]
        for col_name in OUTPUT_COLS:
            if col_name in headers:
                col_pos = headers.index(col_name) + 1   # 1-based
                cell = gspread.utils.rowcol_to_a1(row_idx, col_pos)
                updates.append({
                    "range":  cell,
                    "values": [[str(result.get(col_name, ""))]],
                })

    if not updates:
        print("      Nothing to write.")
        return

    _batch_update_with_retry(sheet, updates)
    print(f"      Written {len(result_map)} rows to Google Sheet")


def save_results(df: pd.DataFrame, output_path: str = "results.csv"):
    """Save classified results to a local CSV as backup."""
    df.to_csv(output_path, index=False)
    print(f"      Results saved -> {output_path}")
