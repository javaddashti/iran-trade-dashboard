
"""
ساخت فایل‌های تجمیعی سلسله‌مراتبی HS برای داشبورد.

قبل از اجرا، فایل‌های زیر باید در data/raw باشند:
    export-all.dta
    import-all.dta
    dd.xlsx
    HS2_semantic_titles_from_1396.xlsx   (اختیاری ولی توصیه‌شده)

اجرا:
    python prepare_hs_detail.py

خروجی‌ها در data/processed:
    hs_hierarchy_national.parquet
    hs_hierarchy_bushehr.parquet
    hs_reference.parquet
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

EXPORT_PATH = RAW / "export-all.dta"
IMPORT_PATH = RAW / "import-all.dta"
HS8_REF_PATH = RAW / "dd.xlsx"
HS2_TITLES_PATH = RAW / "HS2_semantic_titles_from_1396.xlsx"

BUSHEHR_WITHOUT_PARS = {
    "منطقه ویژه اقتصادی بوشهر",
    "گناوه",
    "بندر ریگ",
    "دیلم",
}
PARS_CUSTOM = "منطقه ویژه اقتصادی انرژی پارس"
BUSHEHR_WITH_PARS = BUSHEHR_WITHOUT_PARS | {PARS_CUSTOM}

LEVELS = {
    "HS2": 2,
    "HS4": 4,
    "HS6": 6,
    "HS8": 8,
}

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

def normalize_code(s: pd.Series) -> pd.Series:
    code = (
        s.astype("string")
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"[^0-9]", "", regex=True)
        .str.strip()
    )
    valid = code.str.len().between(1, 8)
    code = code.where(valid)
    return code.str.zfill(8)

def read_trade(path: Path, flow: str) -> pd.DataFrame:
    print(f"Reading {path.name} for HS detail ...")

    needed = ["Year", "Custom", "Tarrif_Code", "Dollar_Value", "Weight_kg"]

    df = pd.read_stata(
        path,
        convert_categoricals=True,
        columns=needed,
    )

    df["Flow"] = flow
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    df["Dollar_Value"] = pd.to_numeric(df["Dollar_Value"], errors="coerce").fillna(0.0)
    df["Weight_kg"] = pd.to_numeric(df["Weight_kg"], errors="coerce").fillna(0.0)

    df["Custom"] = clean_text(df["Custom"])
    df["HS8"] = normalize_code(df["Tarrif_Code"])

    df = df[
        df["Year"].between(1390, 1403, inclusive="both")
        & df["HS8"].notna()
    ].copy()

    return df[["Year", "Flow", "Custom", "HS8", "Dollar_Value", "Weight_kg"]]

def aggregate_levels(df: pd.DataFrame, extra_group_cols=None) -> pd.DataFrame:
    extra_group_cols = extra_group_cols or []
    parts = []

    for level, n in LEVELS.items():
        x = df.copy()
        x["HS_Level"] = level
        x["HS_Code"] = x["HS8"].str.slice(0, n)

        grouped = (
            x.groupby(
                ["Year", "Flow", *extra_group_cols, "HS_Level", "HS_Code"],
                as_index=False,
                dropna=False,
            )[["Dollar_Value", "Weight_kg"]]
            .sum()
        )
        parts.append(grouped)

    return pd.concat(parts, ignore_index=True)

def build_reference() -> pd.DataFrame:
    if not HS8_REF_PATH.exists():
        raise FileNotFoundError(
            f"{HS8_REF_PATH} پیدا نشد. فایل dd.xlsx را داخل data/raw کپی کنید."
        )

    ref = pd.read_excel(HS8_REF_PATH, dtype={"Tarrif_Code": str})

    required = {"Tarrif_Code", "Tarrif_desc"}
    missing = required - set(ref.columns)
    if missing:
        raise ValueError(
            f"ستون‌های لازم در dd.xlsx پیدا نشدند: {sorted(missing)}"
        )

    ref["HS8"] = normalize_code(ref["Tarrif_Code"])
    ref["Tarrif_desc"] = clean_text(ref["Tarrif_desc"])

    # اگر یک کد چند شرح داشته باشد، شرح پرتکرارتر (cc بالاتر) انتخاب می‌شود.
    if "cc" in ref.columns:
        ref["cc"] = pd.to_numeric(ref["cc"], errors="coerce").fillna(0)
        ref = ref.sort_values(["HS8", "cc"], ascending=[True, False])

    ref = ref.dropna(subset=["HS8"]).drop_duplicates("HS8").copy()

    ref["HS2"] = ref["HS8"].str[:2]
    ref["HS4"] = ref["HS8"].str[:4]
    ref["HS6"] = ref["HS8"].str[:6]

    # عنوان معنایی HS2 در صورت وجود فایل قبلی
    ref["HS2_desc"] = pd.NA

    if HS2_TITLES_PATH.exists():
        hs2 = pd.read_excel(HS2_TITLES_PATH, dtype=str)

        code_col = "HS2" if "HS2" in hs2.columns else hs2.columns[0]

        desc_col = None
        for col in hs2.columns:
            col_s = str(col)
            if "شرح" in col_s and "HS2" in col_s:
                desc_col = col
                break

        if desc_col is not None:
            hs2_map = hs2[[code_col, desc_col]].copy()
            hs2_map.columns = ["HS2", "HS2_desc"]
            hs2_map["HS2"] = (
                hs2_map["HS2"]
                .astype("string")
                .str.replace(r"\.0$", "", regex=True)
                .str.replace(r"[^0-9]", "", regex=True)
                .str.zfill(2)
            )
            hs2_map["HS2_desc"] = clean_text(hs2_map["HS2_desc"])
            hs2_map = hs2_map.drop_duplicates("HS2")

            ref = ref.drop(columns=["HS2_desc"]).merge(
                hs2_map, on="HS2", how="left"
            )

    keep = ["HS8", "HS6", "HS4", "HS2", "Tarrif_desc", "HS2_desc"]
    return ref[keep].sort_values("HS8").reset_index(drop=True)

def save(df: pd.DataFrame, filename: str):
    path = OUT / filename
    df.to_parquet(path, index=False)
    print(f"Saved {filename}: {len(df):,} rows")

def main():
    for p in [EXPORT_PATH, IMPORT_PATH, HS8_REF_PATH]:
        if not p.exists():
            raise FileNotFoundError(f"فایل لازم پیدا نشد: {p}")

    national_parts = []
    bushehr_parts = []

    for path, flow in [
        (EXPORT_PATH, "صادرات"),
        (IMPORT_PATH, "واردات"),
    ]:
        df = read_trade(path, flow)

        # ایران
        national_parts.append(aggregate_levels(df))

        # بوشهر بدون پارس جنوبی
        b0 = df[df["Custom"].isin(BUSHEHR_WITHOUT_PARS)].copy()
        b0["Bushehr_Mode"] = "بدون پارس جنوبی"
        bushehr_parts.append(
            aggregate_levels(b0, extra_group_cols=["Bushehr_Mode"])
        )

        # بوشهر با پارس جنوبی
        b1 = df[df["Custom"].isin(BUSHEHR_WITH_PARS)].copy()
        b1["Bushehr_Mode"] = "با پارس جنوبی"
        bushehr_parts.append(
            aggregate_levels(b1, extra_group_cols=["Bushehr_Mode"])
        )

        del df, b0, b1

    national = pd.concat(national_parts, ignore_index=True)
    bushehr = pd.concat(bushehr_parts, ignore_index=True)
    ref = build_reference()

    save(national, "hs_hierarchy_national.parquet")
    save(bushehr, "hs_hierarchy_bushehr.parquet")
    save(ref, "hs_reference.parquet")

    print("\nDone.")
    print("اکنون صفحه کالاها می‌تواند HS2، HS4، HS6 و HS8 را نمایش دهد.")

if __name__ == "__main__":
    main()
