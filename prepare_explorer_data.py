
"""
ساخت دیتای چندبعدی مخصوص «کاوشگر تجارت».

ورودی:
    data/raw/export-all.dta
    data/raw/import-all.dta

خروجی:
    data/processed/explorer/*.parquet

ابعاد:
    Year × Flow × Custom × Country × HS2 × HS4 × HS6 × HS8

شاخص‌ها:
    Dollar_Value
    Rial_Value
    Weight_kg

اجرا:
    python prepare_explorer_data.py
"""

from pathlib import Path
import shutil
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "explorer"

EXPORT_PATH = RAW / "export-all.dta"
IMPORT_PATH = RAW / "import-all.dta"

def clean_text(s: pd.Series) -> pd.Series:
    return (
        s.astype("string")
        .str.replace("ي", "ی", regex=False)
        .str.replace("ى", "ی", regex=False)
        .str.replace("ك", "ک", regex=False)
        .str.replace("\u00a0", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

def normalize_hs8(s: pd.Series) -> pd.Series:
    code = (
        s.astype("string")
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"[^0-9]", "", regex=True)
        .str.strip()
    )
    valid = code.str.len().between(1, 8)
    return code.where(valid).str.zfill(8)

def read_and_write(path: Path, flow: str):
    print(f"Reading {path.name} ...")

    cols = [
        "Year",
        "Custom",
        "Country",
        "Tarrif_Code",
        "Dollar_Value",
        "Rial_Value",
        "Weight_kg",
    ]

    df = pd.read_stata(
        path,
        convert_categoricals=True,
        columns=cols,
    )

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    df["Custom"] = clean_text(df["Custom"]).fillna("نامشخص")
    df["Country"] = clean_text(df["Country"]).fillna("نامشخص")
    df["HS8"] = normalize_hs8(df["Tarrif_Code"]).fillna("")

    for col in ["Dollar_Value", "Rial_Value", "Weight_kg"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["HS2"] = df["HS8"].str[:2]
    df["HS4"] = df["HS8"].str[:4]
    df["HS6"] = df["HS8"].str[:6]
    df["Flow"] = flow

    df = df[df["Year"].between(1390, 1403, inclusive="both")].copy()

    for year in sorted(int(x) for x in df["Year"].dropna().unique()):
        y = df[df["Year"].eq(year)].copy()

        grouped = (
            y.groupby(
                [
                    "Year",
                    "Flow",
                    "Custom",
                    "Country",
                    "HS2",
                    "HS4",
                    "HS6",
                    "HS8",
                ],
                as_index=False,
                dropna=False,
            )[["Dollar_Value", "Rial_Value", "Weight_kg"]]
            .sum()
        )

        flow_en = "export" if flow == "صادرات" else "import"
        out_path = OUT / f"{flow_en}_{year}.parquet"
        grouped.to_parquet(
            out_path,
            index=False,
            compression="zstd",
        )
        print(
            f"Saved {out_path.name}: "
            f"{len(grouped):,} rows, "
            f"{out_path.stat().st_size / 1024 / 1024:,.1f} MB"
        )

    del df

def main():
    for p in [EXPORT_PATH, IMPORT_PATH]:
        if not p.exists():
            raise FileNotFoundError(f"فایل پیدا نشد: {p}")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    read_and_write(EXPORT_PATH, "صادرات")
    read_and_write(IMPORT_PATH, "واردات")

    files = list(OUT.glob("*.parquet"))
    total_mb = sum(p.stat().st_size for p in files) / 1024 / 1024

    print("\nDone.")
    print(f"Files: {len(files)}")
    print(f"Total explorer size: {total_mb:,.1f} MB")
    print("اکنون صفحه «کاوشگر تجارت» قابل استفاده است.")

if __name__ == "__main__":
    main()
