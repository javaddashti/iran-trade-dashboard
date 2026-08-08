from pathlib import Path
import pandas as pd
import streamlit as st

PROCESSED_DIR = Path(__file__).resolve().parent / "data" / "processed"

@st.cache_data(show_spinner=False)
def load_parquet(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"فایل {path.name} پیدا نشد. ابتدا دستور python prepare_data.py را اجرا کنید."
        )
    return pd.read_parquet(path)

def yoy_pct(current, previous):
    if previous is None or pd.isna(previous) or previous == 0:
        return None
    return (current / previous - 1) * 100

def fmt_usd_billion(value):
    if pd.isna(value):
        return "—"
    return f"{value / 1e9:,.1f} میلیارد دلار"

def fmt_million_ton(value_kg):
    if pd.isna(value_kg):
        return "—"
    return f"{value_kg / 1e9:,.1f} میلیون تن"

def fmt_pct(value):
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.1f}٪"

def fmt_usd_per_ton(value):
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.0f} دلار/تن"
