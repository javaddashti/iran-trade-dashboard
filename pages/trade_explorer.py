from pathlib import Path
import re

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

from data_utils import load_hs_reference_bundle
from page_utils import chart_layout
from hs_helpers import label_for

ROOT = Path(__file__).resolve().parents[1]
EXPLORER_DIR = ROOT / "data" / "processed" / "explorer"
_FILE_RE = re.compile(r"^(export|import)_(\d{4})\.parquet$")

st.markdown(
    """
    <div class="trade-hero">
      <div class="trade-hero-title">کاوشگر تجارت</div>
      <div class="trade-hero-subtitle">
        فیلتر همزمان سال، جریان تجارت، گمرک، شریک تجاری و کد HS و مشاهده روند ارزش و وزن
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def explorer_manifest():
    """Return available explorer files parsed from their flow/year filenames."""
    rows = []
    if EXPLORER_DIR.exists():
        for path in EXPLORER_DIR.glob("*.parquet"):
            m = _FILE_RE.match(path.name)
            if not m:
                continue
            flow_en, year = m.groups()
            rows.append(
                {
                    "flow_en": flow_en,
                    "Flow": "صادرات" if flow_en == "export" else "واردات",
                    "Year": int(year),
                    "path": path.as_posix(),
                }
            )
    return pd.DataFrame(rows).sort_values(["Flow", "Year"]) if rows else pd.DataFrame()


manifest = explorer_manifest()
if manifest.empty:
    st.error(
        "دیتای کاوشگر هنوز ساخته نشده است. "
        "ابتدا در ترمینال دستور `python prepare_explorer_data.py` را اجرا کنید."
    )
    st.stop()

try:
    _, hs_maps = load_hs_reference_bundle()
except Exception:
    hs_maps = {"HS2": {}, "HS4": {}, "HS6": {}, "HS8": {}}


def _sql_literal(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def scan_sql(flow: str, year_start: int, year_end: int) -> str:
    """Build a DuckDB read_parquet expression using only relevant files.

    Explorer files are already split by flow and year. Selecting exact files
    prevents every filter change from scanning all export and import years.
    """
    x = manifest[
        manifest["Flow"].eq(flow)
        & manifest["Year"].between(int(year_start), int(year_end), inclusive="both")
    ]
    files = x["path"].tolist()
    if not files:
        return None
    if len(files) == 1:
        return f"read_parquet({_sql_literal(files[0])})"
    file_list = ", ".join(_sql_literal(p) for p in files)
    return f"read_parquet([{file_list}])"


def run_query(sql: str, params=None) -> pd.DataFrame:
    """Execute an uncached DuckDB query.

    Expensive public query functions below are cached by their filter arguments,
    so a connection is only opened for a genuinely new query.
    """
    con = duckdb.connect(database=":memory:")
    try:
        return con.execute(sql, params or []).df()
    finally:
        con.close()


def where_sql(
    flow,
    year_start,
    year_end,
    customs=(),
    countries=(),
    hs2=(),
    hs4=(),
    hs6=(),
    hs8=(),
):
    # Flow/year are already pruned at file level, but the predicates are kept for
    # safety and to make the query valid if files are rebuilt with mixed content.
    clauses = ["Flow = ?", "Year BETWEEN ? AND ?"]
    params = [flow, int(year_start), int(year_end)]

    def add_in(col, values):
        vals = [v for v in values if v not in (None, "")]
        if vals:
            clauses.append(f"{col} IN ({','.join(['?'] * len(vals))})")
            params.extend(vals)

    add_in("Custom", customs)
    add_in("Country", countries)
    add_in("HS2", hs2)
    add_in("HS4", hs4)
    add_in("HS6", hs6)
    add_in("HS8", hs8)

    return " AND ".join(clauses), params


@st.cache_data(show_spinner=False, max_entries=384)
def distinct_values(
    column,
    flow,
    year_start,
    year_end,
    customs=(),
    countries=(),
    hs2=(),
    hs4=(),
    hs6=(),
):
    where, params = where_sql(
        flow,
        year_start,
        year_end,
        customs=customs,
        countries=countries,
        hs2=hs2,
        hs4=hs4,
        hs6=hs6,
    )
    scan = scan_sql(flow, year_start, year_end)
    if scan is None:
        return tuple()
    df = run_query(
        f"""
        SELECT DISTINCT {column} AS value
        FROM {scan}
        WHERE {where}
          AND {column} IS NOT NULL
          AND CAST({column} AS VARCHAR) <> ''
        ORDER BY value
        """,
        params,
    )
    return tuple(df["value"].astype(str).tolist())


@st.cache_data(show_spinner=False, max_entries=256)
def annual_summary(
    flow,
    year_start,
    year_end,
    customs=(),
    countries=(),
    hs2=(),
    hs4=(),
    hs6=(),
    hs8=(),
):
    where, params = where_sql(
        flow,
        year_start,
        year_end,
        customs=customs,
        countries=countries,
        hs2=hs2,
        hs4=hs4,
        hs6=hs6,
        hs8=hs8,
    )
    scan = scan_sql(flow, year_start, year_end)
    if scan is None:
        return pd.DataFrame(
            columns=["Year", "Dollar_Value", "Rial_Value", "Weight_kg", "Unit_Value"]
        )
    return run_query(
        f"""
        SELECT
            Year,
            SUM(Dollar_Value) AS Dollar_Value,
            SUM(Rial_Value) AS Rial_Value,
            SUM(Weight_kg) AS Weight_kg,
            CASE
                WHEN SUM(Weight_kg) > 0
                THEN SUM(Dollar_Value) / (SUM(Weight_kg) / 1000.0)
                ELSE NULL
            END AS Unit_Value
        FROM {scan}
        WHERE {where}
        GROUP BY Year
        ORDER BY Year
        """,
        params,
    )


min_year = int(manifest["Year"].min())
max_year = int(manifest["Year"].max())

# ---------------------------------------------------
# Filters
# ---------------------------------------------------
st.markdown('<div class="section-title">فیلترها</div>', unsafe_allow_html=True)

f1, f2 = st.columns([1, 2])
with f1:
    flow = st.radio("جریان تجارت", ["صادرات", "واردات"], horizontal=True)
with f2:
    year_range = st.slider(
        "بازه سال",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
    )

custom_options = distinct_values("Custom", flow, year_range[0], year_range[1])
customs = st.multiselect(
    "گمرک / گمرک‌های منتخب",
    options=custom_options,
    placeholder="برای مثال: منطقه ویژه اقتصادی بوشهر",
)

country_options = distinct_values(
    "Country",
    flow,
    year_range[0],
    year_range[1],
    customs=tuple(customs),
)
countries = st.multiselect(
    "کشور طرف معامله",
    options=country_options,
    placeholder="برای مثال: امارات متحده عربی یا عمان",
)

st.caption(
    "سطح جغرافیایی این داده «کشور» است، نه شهر. بنابراین برای مثال "
    "تجارت با دبی در داده فعلی به‌صورت «امارات متحده عربی» قابل مشاهده است."
)

# Load HS levels progressively. This avoids sending thousands of HS6/HS8 options
# to the browser before the user has narrowed the hierarchy.
h1, h2, h3, h4 = st.columns(4)

hs2_options = distinct_values(
    "HS2",
    flow,
    year_range[0],
    year_range[1],
    customs=tuple(customs),
    countries=tuple(countries),
)
with h1:
    hs2 = st.multiselect(
        "HS2",
        options=hs2_options,
        format_func=lambda x: label_for(x, "HS2", hs_maps),
    )

hs4_options = ()
if hs2:
    hs4_options = distinct_values(
        "HS4",
        flow,
        year_range[0],
        year_range[1],
        customs=tuple(customs),
        countries=tuple(countries),
        hs2=tuple(hs2),
    )
with h2:
    hs4 = st.multiselect(
        "HS4",
        options=hs4_options,
        format_func=lambda x: label_for(x, "HS4", hs_maps),
        disabled=not bool(hs2),
        placeholder="ابتدا HS2 را انتخاب کنید",
    )

hs6_options = ()
if hs4:
    hs6_options = distinct_values(
        "HS6",
        flow,
        year_range[0],
        year_range[1],
        customs=tuple(customs),
        countries=tuple(countries),
        hs2=tuple(hs2),
        hs4=tuple(hs4),
    )
with h3:
    hs6 = st.multiselect(
        "HS6",
        options=hs6_options,
        format_func=lambda x: label_for(x, "HS6", hs_maps),
        disabled=not bool(hs4),
        placeholder="ابتدا HS4 را انتخاب کنید",
    )

hs8_options = ()
if hs6:
    hs8_options = distinct_values(
        "HS8",
        flow,
        year_range[0],
        year_range[1],
        customs=tuple(customs),
        countries=tuple(countries),
        hs2=tuple(hs2),
        hs4=tuple(hs4),
        hs6=tuple(hs6),
    )
with h4:
    hs8 = st.multiselect(
        "HS8",
        options=hs8_options,
        format_func=lambda x: label_for(x, "HS8", hs_maps),
        disabled=not bool(hs6),
        placeholder="ابتدا HS6 را انتخاب کنید",
    )

current_filters = {
    "flow": flow,
    "year_start": int(year_range[0]),
    "year_end": int(year_range[1]),
    "customs": tuple(customs),
    "countries": tuple(countries),
    "hs2": tuple(hs2),
    "hs4": tuple(hs4),
    "hs6": tuple(hs6),
    "hs8": tuple(hs8),
}

state_key = "trade_explorer_applied_filters"
if state_key not in st.session_state:
    st.session_state[state_key] = current_filters.copy()

apply_col, note_col = st.columns([1, 4])
with apply_col:
    apply_filters = st.button("اعمال فیلترها", type="primary", use_container_width=True)

if apply_filters:
    st.session_state[state_key] = current_filters.copy()

applied_filters = st.session_state[state_key]
filters_dirty = applied_filters != current_filters
with note_col:
    if filters_dirty:
        st.info("فیلترها تغییر کرده‌اند؛ برای به‌روزرسانی نمودارها و شاخص‌ها «اعمال فیلترها» را بزنید.")
    else:
        st.caption("نتایج پایین با فیلترهای فعلی هماهنگ است.")

with st.spinner("در حال محاسبه نتیجه انتخاب‌شده…"):
    annual = annual_summary(**applied_filters)

if annual.empty:
    st.warning("هیچ رکوردی با ترکیب فیلترهای اعمال‌شده پیدا نشد.")
    st.stop()

# ---------------------------------------------------
# KPI
# ---------------------------------------------------
st.divider()
st.markdown('<div class="section-title">خلاصه انتخاب</div>', unsafe_allow_html=True)

total_dollar = annual["Dollar_Value"].sum()
total_rial = annual["Rial_Value"].sum()
total_weight = annual["Weight_kg"].sum()
overall_uv = total_dollar / (total_weight / 1000.0) if total_weight > 0 else None

k1, k2, k3, k4 = st.columns(4)
k1.metric("ارزش دلاری در کل دوره", f"{total_dollar/1e9:,.2f} میلیارد دلار")
k2.metric("ارزش ریالی در کل دوره", f"{total_rial/1e12:,.2f} هزار میلیارد ریال")
k3.metric("وزن در کل دوره", f"{total_weight/1e9:,.2f} میلیون تن")
k4.metric(
    "ارزش هر تن در کل دوره",
    "—" if overall_uv is None else f"{overall_uv:,.0f} دلار/تن",
)

# ---------------------------------------------------
# Trend: render one chart only (instead of computing all tab contents)
# ---------------------------------------------------
st.markdown('<div class="section-title">روند سالانه</div>', unsafe_allow_html=True)
chart_metric = st.radio(
    "معیار نمودار",
    ["ارزش دلاری", "ارزش ریالی", "وزن", "ارزش هر تن"],
    horizontal=True,
    key="explorer_chart_metric",
)

metric_spec = {
    "ارزش دلاری": ("Dollar_Value", 1e9, "میلیارد دلار", "روند ارزش دلاری"),
    "ارزش ریالی": ("Rial_Value", 1e12, "هزار میلیارد ریال", "روند ارزش ریالی"),
    "وزن": ("Weight_kg", 1e9, "میلیون تن", "روند وزن تجارت"),
    "ارزش هر تن": ("Unit_Value", 1.0, "دلار به ازای هر تن", "روند ارزش هر تن"),
}
col, scale, y_label, title = metric_spec[chart_metric]
plot_df = annual[["Year", col]].copy()
plot_df["Value"] = plot_df[col] / scale

fig = px.line(
    plot_df,
    x="Year",
    y="Value",
    markers=True,
    labels={"Year": "سال", "Value": y_label},
)
fig.update_layout(title=title)
fig = chart_layout(fig, height=460, y_title=y_label)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------
# Table
# ---------------------------------------------------
st.markdown('<div class="section-title">جدول سالانه انتخاب</div>', unsafe_allow_html=True)

table = annual.copy()
table["ارزش دلاری (میلیارد دلار)"] = table["Dollar_Value"] / 1e9
table["ارزش ریالی (هزار میلیارد ریال)"] = table["Rial_Value"] / 1e12
table["وزن (میلیون تن)"] = table["Weight_kg"] / 1e9
table["ارزش هر تن (دلار)"] = table["Unit_Value"]

show = table[
    [
        "Year",
        "ارزش دلاری (میلیارد دلار)",
        "ارزش ریالی (هزار میلیارد ریال)",
        "وزن (میلیون تن)",
        "ارزش هر تن (دلار)",
    ]
].rename(columns={"Year": "سال"})

st.dataframe(show, use_container_width=True, hide_index=True)

csv_bytes = show.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "دانلود جدول فیلترشده (CSV)",
    data=csv_bytes,
    file_name="trade_explorer_filtered.csv",
    mime="text/csv",
)

# ---------------------------------------------------
# Selected HS8 descriptions
# ---------------------------------------------------
applied_hs8 = applied_filters.get("hs8", ())
if applied_hs8:
    st.markdown(
        '<div class="section-title">شرح تعرفه‌های HS8 انتخاب‌شده</div>',
        unsafe_allow_html=True,
    )
    for code in applied_hs8:
        st.write(f"**{label_for(code, 'HS8', hs_maps)}**")
