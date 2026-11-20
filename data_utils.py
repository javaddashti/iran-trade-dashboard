from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from hs_helpers import make_reference_maps
from persian_display import fa_digits

PROCESSED_DIR = Path(__file__).resolve().parent / "data" / "processed"

# Columns actually used by the interactive pages. Restricting parquet reads to
# these columns lowers I/O and memory use, especially for HS hierarchy tables.
_TABLE_COLUMNS = {
    "national_annual.parquet": ["Year", "Flow", "Dollar_Value", "Weight_kg"],
    "bushehr_annual.parquet": [
        "Year", "Flow", "Bushehr_Mode", "Dollar_Value", "Weight_kg"
    ],
    "country_annual.parquet": [
        "Year", "Flow", "Country", "Dollar_Value", "Weight_kg"
    ],
    "bushehr_country_annual.parquet": [
        "Year", "Flow", "Country", "Bushehr_Mode", "Dollar_Value", "Weight_kg"
    ],
    "custom_annual.parquet": [
        "Year", "Flow", "Custom", "Dollar_Value", "Weight_kg"
    ],
    "hs_hierarchy_national.parquet": [
        "Year", "Flow", "HS_Level", "HS_Code", "Dollar_Value", "Weight_kg"
    ],
    "hs_hierarchy_bushehr.parquet": [
        "Year", "Flow", "Bushehr_Mode", "HS_Level", "HS_Code",
        "Dollar_Value", "Weight_kg"
    ],
}


def _path_for(name: str) -> Path:
    path = PROCESSED_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"فایل {path.name} پیدا نشد. ابتدا اسکریپت آماده‌سازی داده مربوط را اجرا کنید."
        )
    return path


@st.cache_data(show_spinner=False)
def load_parquet(name: str, columns: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Load a processed parquet file as cached data.

    This loader is best for the small/medium tables where Streamlit's copy-on-read
    behavior is useful. For the large immutable trade tables use
    :func:`load_trade_table` below.
    """
    path = _path_for(name)
    cols = list(columns) if columns else None
    return pd.read_parquet(path, columns=cols)


@st.cache_resource(show_spinner=False)
def load_trade_table(name: str) -> pd.DataFrame:
    """Load a large processed trade table once per app process.

    The returned DataFrame is treated as read-only by the pages. Keeping it as a
    cached resource avoids repeatedly serializing/deserializing large hierarchy
    tables on every Streamlit rerun.
    """
    path = _path_for(name)
    columns = _TABLE_COLUMNS.get(name)

    try:
        df = pd.read_parquet(path, columns=columns)
    except Exception:
        # Backward-compatible fallback if an older parquet schema differs.
        df = pd.read_parquet(path)

    if "Year" in df.columns:
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

    if "HS_Code" in df.columns:
        df["HS_Code"] = df["HS_Code"].astype("string")
    if "HS_Level" in df.columns:
        df["HS_Level"] = df["HS_Level"].astype("string")

    if {"Dollar_Value", "Weight_kg"}.issubset(df.columns):
        dollar = pd.to_numeric(df["Dollar_Value"], errors="coerce")
        weight = pd.to_numeric(df["Weight_kg"], errors="coerce")
        df["Dollar_Value"] = dollar
        df["Weight_kg"] = weight

        unit = np.full(len(df), np.nan, dtype=float)
        valid = weight.gt(0).to_numpy()
        unit[valid] = (
            dollar.to_numpy(dtype=float, na_value=np.nan)[valid]
            / (weight.to_numpy(dtype=float, na_value=np.nan)[valid] / 1000.0)
        )
        unit[~np.isfinite(unit)] = np.nan
        df["Unit_Value"] = unit

    return df


@st.cache_resource(show_spinner=False)
def load_hs_reference_bundle():
    """Load HS reference and build all display maps once per app process."""
    ref = pd.read_parquet(_path_for("hs_reference.parquet"))
    return ref, make_reference_maps(ref)


def yoy_pct(current, previous):
    if previous is None or pd.isna(previous) or previous == 0:
        return None
    return (current / previous - 1) * 100


def fmt_usd_billion(value):
    if pd.isna(value):
        return "—"
    return fa_digits(f"{value / 1e9:,.1f} میلیارد دلار")


def fmt_million_ton(value_kg):
    if pd.isna(value_kg):
        return "—"
    return fa_digits(f"{value_kg / 1e9:,.1f} میلیون تن")


def fmt_pct(value):
    if value is None or pd.isna(value):
        return "—"
    return fa_digits(f"{value:,.1f}٪")


def fmt_usd_per_ton(value):
    if value is None or pd.isna(value):
        return "—"
    return fa_digits(f"{value:,.0f} دلار/تن")
