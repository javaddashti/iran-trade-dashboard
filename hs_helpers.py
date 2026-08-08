
import pandas as pd

def _clean_desc(x):
    if x is None or pd.isna(x):
        return ""
    return " ".join(str(x).split()).strip()

def _representative_parent_desc(group, max_items=2, max_chars=120):
    """
    فایل dd.xlsx عنوان رسمی HS4/HS6 ندارد.
    برای اینکه کد تنها نمایش داده نشود، چند شرح HS8 زیرمجموعه به شکل
    «شامل: ...» نمایش داده می‌شود. این عنوان رسمی HS4/HS6 نیست.
    """
    descs = []
    for x in group["Tarrif_desc"].tolist():
        d = _clean_desc(x)
        if d and d not in descs:
            descs.append(d)
        if len(descs) >= max_items:
            break

    if not descs:
        return ""

    text = "شامل: " + "؛ ".join(descs)
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text

def make_reference_maps(ref: pd.DataFrame):
    maps = {"HS2": {}, "HS4": {}, "HS6": {}, "HS8": {}}

    if ref.empty:
        return maps

    r = ref.copy()
    for col, n in [("HS2",2),("HS4",4),("HS6",6),("HS8",8)]:
        if col in r.columns:
            r[col] = r[col].astype("string").str.zfill(n)

    # HS2: عنوان معنایی موجود
    hs2 = r[["HS2", "HS2_desc"]].drop_duplicates("HS2")
    for _, row in hs2.iterrows():
        code = str(row["HS2"])
        desc = _clean_desc(row.get("HS2_desc"))
        maps["HS2"][code] = f"{code} — {desc}" if desc else f"HS2 {code}"

    # HS4: شرح نماینده از زیرتعرفه‌های HS8
    for code, g in r.groupby("HS4", sort=True):
        code = str(code)
        desc = _representative_parent_desc(g.sort_values("HS8"), max_items=2)
        maps["HS4"][code] = f"{code} — {desc}" if desc else f"HS4 {code}"

    # HS6
    for code, g in r.groupby("HS6", sort=True):
        code = str(code)
        desc = _representative_parent_desc(g.sort_values("HS8"), max_items=2)
        maps["HS6"][code] = f"{code} — {desc}" if desc else f"HS6 {code}"

    # HS8: شرح دقیق
    hs8 = r[["HS8", "Tarrif_desc"]].drop_duplicates("HS8")
    for _, row in hs8.iterrows():
        code = str(row["HS8"])
        desc = _clean_desc(row.get("Tarrif_desc"))
        maps["HS8"][code] = f"{code} — {desc}" if desc else code

    return maps

def label_for(code, level, maps):
    if code is None:
        return "همه"
    return maps.get(level, {}).get(str(code), str(code))

def short_label_for(code, level, maps, max_chars=70):
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
        x = x[x["HS_Code"].astype(str).str.startswith(str(parent_code))]
    return sorted(x["HS_Code"].dropna().astype(str).unique())
