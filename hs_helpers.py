
import pandas as pd


def _clean_desc(x):
    if x is None or pd.isna(x):
        return ""
    return " ".join(str(x).split()).strip()


def _first_nonempty(series):
    for x in series:
        d = _clean_desc(x)
        if d:
            return d
    return ""


def make_reference_maps(ref: pd.DataFrame):
    """
    خروجی:
        maps["HS2"][code] = "03 — ماهی و آبزیان"
        maps["HS4"][code] = "2711 — گازهای نفتی و سایر هیدروکربورهای گازی شکل"
        maps["HS6"][code] = "271119 — سایر"
        maps["HS8"][code] = "27111990 — شرح دقیق تعرفه"

    اگر فایل مرجع قدیمی باشد و HS4_desc / HS6_desc نداشته باشد،
    کد همچنان قابل نمایش است.
    """
    maps = {"HS2": {}, "HS4": {}, "HS6": {}, "HS8": {}}

    if ref is None or ref.empty:
        return maps

    r = ref.copy()

    for col, n in [
        ("HS2", 2),
        ("HS4", 4),
        ("HS6", 6),
        ("HS8", 8),
    ]:
        if col in r.columns:
            r[col] = r[col].astype("string").str.zfill(n)

    # HS2
    if "HS2" in r.columns:
        cols = ["HS2"]
        if "HS2_desc" in r.columns:
            cols.append("HS2_desc")

        hs2 = r[cols].drop_duplicates("HS2")

        for _, row in hs2.iterrows():
            code = str(row["HS2"])
            desc = _clean_desc(row.get("HS2_desc"))
            maps["HS2"][code] = (
                f"{code} — {desc}" if desc else f"HS2 {code}"
            )

    # HS4: عنوان رسمی کتاب مقررات ۱۳۹۶
    if "HS4" in r.columns:
        grouped = r.groupby("HS4", sort=True, dropna=True)

        for code, g in grouped:
            code = str(code)
            desc = (
                _first_nonempty(g["HS4_desc"])
                if "HS4_desc" in g.columns
                else ""
            )

            maps["HS4"][code] = (
                f"{code} — {desc}" if desc else f"HS4 {code}"
            )

    # HS6: عنوان رسمی کتاب مقررات ۱۳۹۶
    if "HS6" in r.columns:
        grouped = r.groupby("HS6", sort=True, dropna=True)

        for code, g in grouped:
            code = str(code)
            desc = (
                _first_nonempty(g["HS6_desc"])
                if "HS6_desc" in g.columns
                else ""
            )

            # بعضی شرح‌های رسمی HS6 مثل «سایر» کوتاه‌اند؛
            # خود عنوان رسمی را بدون دستکاری نگه می‌داریم.
            maps["HS6"][code] = (
                f"{code} — {desc}" if desc else f"HS6 {code}"
            )

    # HS8
    if "HS8" in r.columns:
        desc_col = None

        if "HS8_desc" in r.columns:
            desc_col = "HS8_desc"
        elif "Tarrif_desc" in r.columns:
            desc_col = "Tarrif_desc"

        cols = ["HS8"]
        if desc_col:
            cols.append(desc_col)

        hs8 = r[cols].drop_duplicates("HS8")

        for _, row in hs8.iterrows():
            code = str(row["HS8"])
            desc = (
                _clean_desc(row.get(desc_col))
                if desc_col
                else ""
            )

            maps["HS8"][code] = (
                f"{code} — {desc}" if desc else code
            )

    return maps


def description_for(code, level, ref: pd.DataFrame):
    """فقط شرح رسمی/مرجع کد را برمی‌گرداند، بدون خود کد."""
    if code is None or ref is None or ref.empty:
        return ""

    code = str(code)

    desc_col = {
        "HS2": "HS2_desc",
        "HS4": "HS4_desc",
        "HS6": "HS6_desc",
        "HS8": "HS8_desc",
    }.get(level)

    if not desc_col or desc_col not in ref.columns:
        if level == "HS8" and "Tarrif_desc" in ref.columns:
            desc_col = "Tarrif_desc"
        else:
            return ""

    x = ref[
        ref[level].astype("string").str.zfill(
            {"HS2":2,"HS4":4,"HS6":6,"HS8":8}[level]
        ).eq(code)
    ]

    if x.empty:
        return ""

    return _first_nonempty(x[desc_col])


def label_for(code, level, maps):
    if code is None:
        return "همه"
    return maps.get(level, {}).get(str(code), str(code))


def short_label_for(code, level, maps, max_chars=88):
    label = label_for(code, level, maps)

    if len(label) <= max_chars:
        return label

    return label[: max_chars - 1].rstrip() + "…"


def deepest_selected(hs2=None, hs4=None, hs6=None, hs8=None):
    if hs8:
        return "HS8", hs8
    if hs6:
        return "HS6", hs6
    if hs4:
        return "HS4", hs4
    if hs2:
        return "HS2", hs2
    return None, None


def child_codes(hierarchy, level, parent_code=None):
    x = hierarchy[hierarchy["HS_Level"].eq(level)]

    if parent_code:
        x = x[
            x["HS_Code"]
            .astype(str)
            .str.startswith(str(parent_code))
        ]

    return sorted(
        x["HS_Code"]
        .dropna()
        .astype(str)
        .unique()
    )
