"""
One-time annual preprocessing for the foreign-trade dashboard.

Put these files in data/raw before running:
    export-all.dta
    import-all.dta
    HS2_semantic_titles_from_1396.xlsx

Then run:
    python prepare_data.py
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

EXPORT_PATH = RAW / "export-all.dta"
IMPORT_PATH = RAW / "import-all.dta"
HS2_PATH = RAW / "HS2_semantic_titles_from_1396.xlsx"

BUSHEHR_WITHOUT_PARS = {
    "منطقه ویژه اقتصادی بوشهر",
    "گناوه",
    "بندر ریگ",
    "دیلم",
}

PARS_CUSTOM = "منطقه ویژه اقتصادی انرژی پارس"
BUSHEHR_WITH_PARS = BUSHEHR_WITHOUT_PARS | {PARS_CUSTOM}

REQUIRED_COLS = [
    "Year",
    "Custom",
    "Country",
    "Tarrif_Code",
    "Dollar_Value",
    "Weight_kg",
]

def clean_text_series(s: pd.Series) -> pd.Series:
    return (
        s.astype("string")
        .str.replace("ي", "ی", regex=False)
        .str.replace("ك", "ک", regex=False)
        .str.replace("\u00a0", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

def standardize_frame(path: Path, flow: str) -> pd.DataFrame:
    print(f"Reading {path.name} ...")
    df = pd.read_stata(path, convert_categoricals=True)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing columns: {missing}")

    # Keep only columns needed for the annual dashboard.
    df = df[REQUIRED_COLS].copy()
    df["Flow"] = flow

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    df["Dollar_Value"] = pd.to_numeric(df["Dollar_Value"], errors="coerce").fillna(0.0)
    df["Weight_kg"] = pd.to_numeric(df["Weight_kg"], errors="coerce").fillna(0.0)

    for col in ["Custom", "Country", "Tarrif_Code"]:
        df[col] = clean_text_series(df[col])

    # Tarrif_Code was encoded in Stata. With convert_categoricals=True,
    # pandas reads the original Stata value labels, i.e. the tariff-code strings.
    code = (
        df["Tarrif_Code"]
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"[^0-9]", "", regex=True)
    )
    df["Tarrif_Code"] = code
    df["HS2"] = code.str.slice(0, 2)
    df["HS4"] = code.str.slice(0, 4)

    df = df[df["Year"].between(1390, 1403, inclusive="both")].copy()
    return df

def aggregate_flow(df: pd.DataFrame):
    metrics = {"Dollar_Value": "sum", "Weight_kg": "sum"}

    national = (
        df.groupby(["Year", "Flow"], dropna=False, as_index=False)
          .agg(metrics)
    )

    custom = (
        df.groupby(["Year", "Flow", "Custom"], dropna=False, as_index=False)
          .agg(metrics)
    )

    country = (
        df[df["Country"].notna()]
        .groupby(["Year", "Flow", "Country"], dropna=False, as_index=False)
        .agg(metrics)
    )

    hs2 = (
        df[df["HS2"].str.len().eq(2).fillna(False)]
        .groupby(["Year", "Flow", "HS2"], dropna=False, as_index=False)
        .agg(metrics)
    )

    def bushehr_tables(customs, mode):
        b = df[df["Custom"].isin(customs)].copy()
        b_total = (
            b.groupby(["Year", "Flow"], as_index=False)
             .agg(metrics)
        )
        b_total["Bushehr_Mode"] = mode

        b_country = (
            b[b["Country"].notna()]
            .groupby(["Year", "Flow", "Country"], as_index=False)
            .agg(metrics)
        )
        b_country["Bushehr_Mode"] = mode

        b_hs2 = (
            b[b["HS2"].str.len().eq(2).fillna(False)]
            .groupby(["Year", "Flow", "HS2"], as_index=False)
            .agg(metrics)
        )
        b_hs2["Bushehr_Mode"] = mode

        return b_total, b_country, b_hs2

    b0 = bushehr_tables(BUSHEHR_WITHOUT_PARS, "بدون پارس جنوبی")
    b1 = bushehr_tables(BUSHEHR_WITH_PARS, "با پارس جنوبی")

    return {
        "national": national,
        "custom": custom,
        "country": country,
        "hs2": hs2,
        "bushehr": pd.concat([b0[0], b1[0]], ignore_index=True),
        "bushehr_country": pd.concat([b0[1], b1[1]], ignore_index=True),
        "bushehr_hs2": pd.concat([b0[2], b1[2]], ignore_index=True),
    }

def read_hs2_titles():
    if not HS2_PATH.exists():
        print("HS2 title file not found; dashboard will use HS2 codes only.")
        return pd.DataFrame(columns=["HS2", "HS2_desc", "HS2_desc_eng"])

    hs = pd.read_excel(HS2_PATH, sheet_name="HS2_titles", dtype={"HS2": str})
    rename_map = {
        "شرح پیشنهادی HS2": "HS2_desc",
        "English concise title": "HS2_desc_eng",
    }
    hs = hs.rename(columns=rename_map)
    hs["HS2"] = hs["HS2"].astype("string").str.zfill(2)
    keep = [c for c in ["HS2", "HS2_desc", "HS2_desc_eng"] if c in hs.columns]
    return hs[keep].drop_duplicates("HS2")

def save(df, name):
    path = OUT / name
    df.to_parquet(path, index=False)
    print(f"Saved {path.name}: {len(df):,} rows")

def main():
    for p in [EXPORT_PATH, IMPORT_PATH]:
        if not p.exists():
            raise FileNotFoundError(
                f"{p} not found.\n"
                "Copy export-all.dta and import-all.dta into data/raw."
            )

    outputs = {
        "national": [],
        "custom": [],
        "country": [],
        "hs2": [],
        "bushehr": [],
        "bushehr_country": [],
        "bushehr_hs2": [],
    }

    for path, flow in [(EXPORT_PATH, "صادرات"), (IMPORT_PATH, "واردات")]:
        df = standardize_frame(path, flow)
        aggs = aggregate_flow(df)
        for key in outputs:
            outputs[key].append(aggs[key])
        del df

    combined = {
        key: pd.concat(parts, ignore_index=True)
        for key, parts in outputs.items()
    }

    # Add HS2 titles to the two HS2 summary files.
    hs_titles = read_hs2_titles()
    if not hs_titles.empty:
        combined["hs2"] = combined["hs2"].merge(hs_titles, on="HS2", how="left")
        combined["bushehr_hs2"] = combined["bushehr_hs2"].merge(hs_titles, on="HS2", how="left")

    save(combined["national"], "national_annual.parquet")
    save(combined["custom"], "custom_annual.parquet")
    save(combined["country"], "country_annual.parquet")
    save(combined["hs2"], "hs2_annual.parquet")
    save(combined["bushehr"], "bushehr_annual.parquet")
    save(combined["bushehr_country"], "bushehr_country_annual.parquet")
    save(combined["bushehr_hs2"], "bushehr_hs2_annual.parquet")

    print("\nDone.")
    print("Next command:")
    print("    streamlit run app.py")

if __name__ == "__main__":
    main()
