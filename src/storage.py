"""
Persistent storage layer — "Results Database" tab in Google Sheets.

Read path  : Google Sheets → session_state DataFrame (on first access)
Write path : merge into session_state + rewrite sheet

Works identically on local (.env) and Streamlit Cloud (st.secrets).
"""

import time
import pandas as pd
import streamlit as st
from datetime import datetime

from src.credentials import _get_client, _get_sheet_id

RESULTS_SHEET_NAME = "Results Database"

RESULT_COLUMNS = [
    "ASIN", "Title", "Brand", "Category",
    "Status", "Returnable?", "Confidence", "Reason",
    "Classified By", "Run Date", "Source File",
]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_results_ws():
    """Return (or create) the Results Database worksheet."""
    client = _get_client()
    sheet_id = _get_sheet_id()
    spreadsheet = client.open_by_key(sheet_id)

    existing = [ws.title for ws in spreadsheet.worksheets()]
    if RESULTS_SHEET_NAME not in existing:
        ws = spreadsheet.add_worksheet(title=RESULTS_SHEET_NAME, rows=2000, cols=len(RESULT_COLUMNS))
        ws.append_row(RESULT_COLUMNS)
        time.sleep(0.5)
    else:
        ws = spreadsheet.worksheet(RESULTS_SHEET_NAME)
    return ws


# ── Public API ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_results_db() -> pd.DataFrame:
    """
    Load all results from Google Sheets.
    Cached for 5 minutes so repeated page navigations don't hit the API.
    Returns empty DataFrame immediately if credentials are not configured.
    """
    from src.credentials import has_credentials
    if not has_credentials():
        return pd.DataFrame(columns=RESULT_COLUMNS)
    try:
        ws = _get_results_ws()
        records = ws.get_all_records()
        if not records:
            return pd.DataFrame(columns=RESULT_COLUMNS)
        df = pd.DataFrame(records)
        # Deduplicate — keep latest entry per ASIN
        df = df.drop_duplicates(subset="ASIN", keep="last").reset_index(drop=True)
        return df
    except Exception as e:
        st.warning(f"Could not load Results Database: {e}")
        return pd.DataFrame(columns=RESULT_COLUMNS)


def invalidate_cache():
    """Call after writes so next load_results_db() re-fetches from Sheets."""
    load_results_db.clear()


def upsert_results(rows: list[dict], source_file: str = "") -> int:
    """
    Merge new classification rows into the Results Database.

    Parameters
    ----------
    rows        : list of dicts with keys matching classifier output
    source_file : name of the uploaded file (for audit trail)

    Returns
    -------
    Number of rows written (new + updated).
    """
    if not rows:
        return 0

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Normalise incoming rows to sheet column format
    def _normalise(r: dict) -> dict:
        return {
            "ASIN":          str(r.get("asin",  r.get("ASIN",  ""))).upper().strip(),
            "Title":         str(r.get("title", r.get("Title", ""))).strip(),
            "Brand":         str(r.get("brand", r.get("Brand", ""))).strip(),
            "Category":      str(r.get("category", r.get("Category", ""))).strip(),
            "Status":        str(r.get("status", r.get("Status", "Unknown"))).strip(),
            "Returnable?":   str(r.get("returnable", r.get("Returnable?", "Review"))).strip(),
            "Confidence":    str(r.get("confidence", r.get("Confidence", "Low"))).strip(),
            "Reason":        str(r.get("reason", r.get("Reason", ""))).strip(),
            "Classified By": str(r.get("classified_by", r.get("Classified By", "rules"))).strip(),
            "Run Date":      str(r.get("run_date", r.get("Run Date", timestamp))).strip(),
            "Source File":   source_file or str(r.get("Source File", "")).strip(),
        }

    new_map = {_normalise(r)["ASIN"]: _normalise(r) for r in rows}

    try:
        ws = _get_results_ws()

        # Load current state
        records = ws.get_all_records()
        current_map = {str(rec.get("ASIN", "")).upper(): rec for rec in records}

        # Merge
        current_map.update(new_map)

        # Rewrite sheet (2 API calls: clear + update)
        all_rows = [[rec.get(col, "") for col in RESULT_COLUMNS]
                    for rec in current_map.values()]

        ws.clear()
        ws.update(
            range_name="A1",
            values=[RESULT_COLUMNS] + all_rows,
            value_input_option="USER_ENTERED",
        )
    except Exception as e:
        st.error(f"Failed to write to Results Database: {e}")
        return 0

    invalidate_cache()
    return len(new_map)


def get_stats(df: pd.DataFrame | None = None) -> dict:
    """Compute KPI stats from the results DataFrame."""
    if df is None:
        df = load_results_db()

    if df.empty:
        return {
            "total": 0, "non_returnable": 0, "returnable": 0, "unknown": 0,
            "non_ret_pct": 0.0, "ret_pct": 0.0, "unknown_pct": 0.0,
            "high_confidence": 0, "confidence_pct": 0.0,
        }

    total     = len(df)
    non_ret   = (df["Status"] == "Non-Returnable").sum()
    ret       = (df["Status"] == "Returnable").sum()
    unknown   = (df["Status"] == "Unknown").sum()
    high_conf = (df["Confidence"] == "High").sum()

    return {
        "total":           total,
        "non_returnable":  int(non_ret),
        "returnable":      int(ret),
        "unknown":         int(unknown),
        "non_ret_pct":     round(non_ret / total * 100, 1),
        "ret_pct":         round(ret    / total * 100, 1),
        "unknown_pct":     round(unknown / total * 100, 1),
        "high_confidence": int(high_conf),
        "confidence_pct":  round(high_conf / total * 100, 1),
    }


def get_known_asins(df: pd.DataFrame | None = None) -> set:
    """Return set of all ASINs already in the database."""
    if df is None:
        df = load_results_db()
    if df.empty:
        return set()
    asin_col = df["ASIN"]
    if isinstance(asin_col, pd.DataFrame):
        asin_col = asin_col.iloc[:, 0]
    return set(asin_col.str.upper().tolist())
