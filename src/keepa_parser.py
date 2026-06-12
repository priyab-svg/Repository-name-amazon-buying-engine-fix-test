"""
Keepa XLSX export parser.
Normalises any Keepa product export into the standard fields
used by ReturnabilityClassifier.
"""

from io import BytesIO
import pandas as pd

# ── Column name aliases (Keepa changes names between export types) ──────────
_ALIAS = {
    # ASIN
    "asin":                   "asin",
    "Asin":                   "asin",
    "ASIN":                   "asin",
    # Title
    "Product Name":           "title",
    "Title":                  "title",
    "product name":           "title",
    # Brand
    "Brand":                  "brand",
    "Manufacturer":           "brand",
    "brand":                  "brand",
    # Category
    "Category":               "category",
    "Root Category":          "category",
    "category":               "category",
    # Description
    "Description":            "description",
    "description":            "description",
    # Keepa flag columns (kept as-is for _check_keepa_export)
    "Is HazMat":              "Is HazMat",
    "Is heat sensitive":      "Is heat sensitive",
    "Adult Product":          "Adult Product",
    "Batteries Required":     "Batteries Required",
    "Batteries Included":     "Batteries Included",
    "Hazardous Materials":    "Hazardous Materials",
    "Safety Warning":         "Safety Warning",
    "Item Type":              "Item Type",
    "Material":               "Material",
    "Ingredients":            "Ingredients",
}

KEEPA_SIGNAL_COLS = [
    "Is HazMat", "Is heat sensitive", "Adult Product",
    "Batteries Required", "Batteries Included",
    "Hazardous Materials", "Safety Warning",
    "Item Type", "Material", "Ingredients",
]


def parse_keepa_xlsx(file_bytes: bytes) -> tuple[pd.DataFrame, dict]:
    """
    Parse a Keepa XLSX export.

    Returns
    -------
    df          : normalised DataFrame (asin, title, brand, category, description)
    keepa_export: dict {ASIN: {signal_col: value, ...}} for classifier
    """
    df = pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
    df.columns = df.columns.str.strip()

    # Rename to normalised names
    df = df.rename(columns={k: v for k, v in _ALIAS.items() if k in df.columns})

    # Drop duplicate columns — Keepa exports can include both "ASIN" and "asin"
    # headers; both alias to "asin", leaving two identical column names.
    # df["asin"] then returns a DataFrame instead of a Series, and DataFrame
    # has no .str accessor → 'DataFrame' object has no attribute 'str'.
    df = df.loc[:, ~df.columns.duplicated(keep="first")]

    # Validate ASIN column exists
    if "asin" not in df.columns:
        raise ValueError(
            "Could not find an ASIN column in the uploaded file.\n"
            "Please upload a Keepa Product Viewer export that includes an 'ASIN' column."
        )

    # Clean & validate ASINs
    asin_col = df["asin"]
    if isinstance(asin_col, pd.DataFrame):
        asin_col = asin_col.iloc[:, 0]
    df["asin"] = asin_col.astype(str).str.strip().str.upper()
    df = df[df["asin"].str.match(r"^[A-Z0-9]{10}$")].copy()

    if df.empty:
        raise ValueError("No valid ASINs found in the uploaded file.")

    # Fill missing standard columns
    for col in ["title", "brand", "category", "description"]:
        if col not in df.columns:
            df[col] = ""
        series = df[col]
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        df[col] = series.fillna("").astype(str).str.strip()

    # Build keepa_export lookup dict
    keepa_export = {}
    for _, row in df.iterrows():
        asin = row["asin"]
        signals = {}
        for col in KEEPA_SIGNAL_COLS:
            if col in df.columns:
                signals[col] = str(row.get(col, "")).strip()
        keepa_export[asin] = signals

    # Return only the standard columns in df
    keep_cols = ["asin", "title", "brand", "category", "description"] + \
                [c for c in KEEPA_SIGNAL_COLS if c in df.columns]
    df = df[[c for c in keep_cols if c in df.columns]].copy()

    return df, keepa_export


def detected_columns(df: pd.DataFrame) -> dict:
    """Return a summary of which important columns were found."""
    standard = ["title", "brand", "category", "description"]
    signals  = KEEPA_SIGNAL_COLS
    return {
        "standard_found": [c for c in standard  if c in df.columns and df[c].astype(bool).any()],
        "signals_found":  [c for c in signals   if c in df.columns and df[c].astype(bool).any()],
        "standard_missing": [c for c in standard if c not in df.columns],
    }
