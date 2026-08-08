
"""
ساخت مرجع رسمی عناوین HS برای داشبورد.

منابع:
1) کتاب مقررات صادرات و واردات ۱۳۹۶:
   - عنوان رسمی HS4
   - عنوان رسمی HS6
   - عنوان/شرح HS8 و معادل انگلیسی در صورت وجود
2) dd.xlsx:
   - شرح HS8 استخراج‌شده از داده تجارت؛ در HS8 بر کتاب ۱۳۹۶ اولویت دارد
3) HS2_semantic_titles_from_1396*.xlsx:
   - عنوان کوتاه و خوانای HS2

این اسکریپت فقط فایل مرجع HS را بازسازی می‌کند و نیازی به خواندن
export-all.dta یا import-all.dta ندارد.

اجرا:
    python prepare_hs_reference_official.py

خروجی:
    data/processed/hs_reference.parquet
    data/processed/hs_reference_audit.xlsx
"""

from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)


def find_one(patterns, required=True):
    matches = []
    for pattern in patterns:
        matches.extend(RAW.glob(pattern))
    # حذف تکراری‌ها و مرتب‌سازی
    matches = sorted(set(matches))
    if matches:
        return matches[0]
    if required:
        raise FileNotFoundError(
            "هیچ فایلی با الگوهای زیر در data/raw پیدا نشد:\n"
            + "\n".join(f"  - {p}" for p in patterns)
        )
    return None


def clean_desc(value):
    if pd.isna(value):
        return pd.NA

    s = str(value)
    s = (
        s.replace("_x000D_", " ")
         .replace("\r", " ")
         .replace("\n", " ")
         .replace("ي", "ی")
         .replace("ى", "ی")
         .replace("ك", "ک")
         .replace("\u00a0", " ")
    )

    s = re.sub(r"\s+", " ", s).strip()

    # علائم سلسله‌مراتبی ابتدای شرح در کتاب را حذف می‌کنیم،
    # اما متن رسمی شرح را نگه می‌داریم.
    s = re.sub(r"^[\-\–\—ـ•\s]+", "", s).strip()

    return s if s else pd.NA


def normalize_book_code(value):
    if pd.isna(value):
        return pd.NA

    code = re.sub(r"\D", "", str(value))
    if len(code) not in (4, 6, 8):
        return pd.NA
    return code


def normalize_hs8(value):
    if pd.isna(value):
        return pd.NA

    code = re.sub(r"\D", "", str(value))
    if not code:
        return pd.NA

    if len(code) <= 8:
        code = code.zfill(8)

    if len(code) != 8:
        return pd.NA

    return code


def read_book(book_path):
    book = pd.read_excel(book_path, sheet_name="ورقه1", dtype=object)

    code_col = next(
        c for c in book.columns
        if "شمارهتعرفه" in str(c).replace(" ", "")
    )
    desc_fa_col = next(
        c for c in book.columns
        if "شرحکالا" in str(c).replace(" ", "")
    )
    desc_en_col = "MAS" if "MAS" in book.columns else None

    book["Code"] = book[code_col].map(normalize_book_code)
    book["Desc_FA"] = book[desc_fa_col].map(clean_desc)

    if desc_en_col:
        book["Desc_EN"] = book[desc_en_col].map(clean_desc)
    else:
        book["Desc_EN"] = pd.NA

    tables = {}

    for level, n in [("HS4", 4), ("HS6", 6), ("HS8", 8)]:
        x = book[
            book["Code"].fillna("").astype(str).str.len().eq(n)
        ][["Code", "Desc_FA", "Desc_EN"]].copy()

        # HS4 و HS6 در کتاب یکتا هستند.
        # در HS8 چند مورد تکراری وجود دارد؛ اولین شرح را به‌عنوان fallback نگه می‌داریم.
        x = x.dropna(subset=["Code"]).drop_duplicates("Code", keep="first")
        x = x.rename(
            columns={
                "Code": level,
                "Desc_FA": f"{level}_desc",
                "Desc_EN": f"{level}_desc_eng",
            }
        )
        tables[level] = x

    return tables


def read_dd(dd_path):
    dd = pd.read_excel(dd_path, dtype={"Tarrif_Code": str})

    required = {"Tarrif_Code", "Tarrif_desc"}
    missing = required - set(dd.columns)
    if missing:
        raise ValueError(
            f"ستون‌های لازم در dd.xlsx پیدا نشد: {sorted(missing)}"
        )

    dd["HS8"] = dd["Tarrif_Code"].map(normalize_hs8)
    dd["DD_HS8_desc"] = dd["Tarrif_desc"].map(clean_desc)

    if "cc" in dd.columns:
        dd["cc"] = pd.to_numeric(dd["cc"], errors="coerce").fillna(0)
        # اگر یک کد چند شرح دارد، شرح پرتکرارتر را نگه می‌داریم.
        dd = dd.sort_values(["HS8", "cc"], ascending=[True, False])

    dd = (
        dd.dropna(subset=["HS8"])
          .drop_duplicates("HS8", keep="first")
    )

    return dd[["HS8", "DD_HS8_desc"]]


def read_hs2(hs2_path):
    if hs2_path is None:
        return pd.DataFrame(
            columns=["HS2", "HS2_desc", "HS2_desc_eng"]
        )

    hs2 = pd.read_excel(hs2_path, dtype=object)

    code_col = "HS2" if "HS2" in hs2.columns else hs2.columns[0]

    fa_col = None
    en_col = None

    for col in hs2.columns:
        col_s = str(col)
        if fa_col is None and "شرح" in col_s and "HS2" in col_s:
            fa_col = col
        if en_col is None and "English" in col_s:
            en_col = col

    out = pd.DataFrame()
    out["HS2"] = (
        hs2[code_col]
        .astype("string")
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"[^0-9]", "", regex=True)
        .str.zfill(2)
    )

    out["HS2_desc"] = (
        hs2[fa_col].map(clean_desc)
        if fa_col is not None
        else pd.NA
    )

    out["HS2_desc_eng"] = (
        hs2[en_col].map(clean_desc)
        if en_col is not None
        else pd.NA
    )

    return out.drop_duplicates("HS2")


def main():
    book_path = find_one(
        [
            "*کتاب مقررات صادرات و واردات*96*.xlsx",
            "*کتاب مقررات صادرات و واردات*۹۶*.xlsx",
            "*کتاب مقررات صادرات و واردات*.xlsx",
        ]
    )

    dd_path = find_one(["dd.xlsx", "dd*.xlsx"])

    hs2_path = find_one(
        [
            "HS2_semantic_titles_from_1396*.xlsx",
            "*HS2*semantic*1396*.xlsx",
        ],
        required=False,
    )

    print(f"Book: {book_path.name}")
    print(f"HS8 reference: {dd_path.name}")
    if hs2_path:
        print(f"HS2 titles: {hs2_path.name}")
    else:
        print("HS2 semantic titles file not found; HS2 codes will remain available.")

    book_tables = read_book(book_path)
    dd = read_dd(dd_path)
    hs2 = read_hs2(hs2_path)

    book_hs8 = book_tables["HS8"]

    # Universe: همه HS8های dd و کتاب ۱۳۹۶
    universe = sorted(
        set(dd["HS8"].dropna().astype(str))
        | set(book_hs8["HS8"].dropna().astype(str))
    )

    ref = pd.DataFrame({"HS8": universe})
    ref["HS6"] = ref["HS8"].str[:6]
    ref["HS4"] = ref["HS8"].str[:4]
    ref["HS2"] = ref["HS8"].str[:2]

    # عنوان رسمی HS4 و HS6 از کتاب مقررات ۱۳۹۶
    ref = ref.merge(
        book_tables["HS4"],
        on="HS4",
        how="left",
    )
    ref = ref.merge(
        book_tables["HS6"],
        on="HS6",
        how="left",
    )

    # HS8 کتاب + dd
    ref = ref.merge(
        book_hs8,
        on="HS8",
        how="left",
    )
    ref = ref.merge(
        dd,
        on="HS8",
        how="left",
    )

    # در HS8، dd از آنجا که از داده مورد استفاده پروژه استخراج شده،
    # بر شرح کتاب ۱۳۹۶ اولویت دارد.
    ref["HS8_desc"] = ref["DD_HS8_desc"].combine_first(ref["HS8_desc"])

    # alias سازگار با کدهای قبلی داشبورد
    ref["Tarrif_desc"] = ref["HS8_desc"]

    # HS2
    if not hs2.empty:
        ref = ref.merge(hs2, on="HS2", how="left")
    else:
        ref["HS2_desc"] = pd.NA
        ref["HS2_desc_eng"] = pd.NA

    ref["HS4_source"] = "کتاب مقررات صادرات و واردات ۱۳۹۶"
    ref["HS6_source"] = "کتاب مقررات صادرات و واردات ۱۳۹۶"
    ref["HS8_source"] = ref["DD_HS8_desc"].notna().map(
        {
            True: "dd.xlsx / داده پروژه",
            False: "کتاب مقررات صادرات و واردات ۱۳۹۶",
        }
    )

    keep = [
        "HS2",
        "HS2_desc",
        "HS2_desc_eng",
        "HS4",
        "HS4_desc",
        "HS4_desc_eng",
        "HS6",
        "HS6_desc",
        "HS6_desc_eng",
        "HS8",
        "HS8_desc",
        "HS8_desc_eng",
        "Tarrif_desc",
        "HS4_source",
        "HS6_source",
        "HS8_source",
    ]

    ref = (
        ref[keep]
        .sort_values("HS8")
        .reset_index(drop=True)
    )

    out_parquet = PROCESSED / "hs_reference.parquet"
    out_excel = PROCESSED / "hs_reference_audit.xlsx"

    ref.to_parquet(out_parquet, index=False)
    ref.to_excel(out_excel, index=False)

    print("\nDone.")
    print(f"HS8 rows: {len(ref):,}")
    print(f"HS4 with official Persian title: {ref[['HS4','HS4_desc']].drop_duplicates()['HS4_desc'].notna().sum():,}")
    print(f"HS6 with official Persian title: {ref[['HS6','HS6_desc']].drop_duplicates()['HS6_desc'].notna().sum():,}")
    print(f"HS8 with Persian description: {ref['HS8_desc'].notna().sum():,}")
    print(f"Saved: {out_parquet}")
    print(f"Audit file: {out_excel}")
    print("\nRestart Streamlit so cached labels are refreshed.")


if __name__ == "__main__":
    main()
