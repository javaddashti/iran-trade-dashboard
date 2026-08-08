
from pathlib import Path
import io

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

from data_utils import load_parquet
from page_utils import chart_layout
from hs_helpers import make_reference_maps, label_for

ROOT = Path(__file__).resolve().parents[1]
EXPLORER_DIR = ROOT / "data" / "processed" / "explorer"
GLOB = (EXPLORER_DIR / "*.parquet").as_posix().replace("'", "''")

st.markdown("""
<div class="trade-hero">
  <div class="trade-hero-title">کاوشگر تجارت</div>
  <div class="trade-hero-subtitle">
    فیلتر همزمان سال، جریان تجارت، گمرک، شریک تجاری و کد HS و مشاهده روند ارزش و وزن
  </div>
</div>
""", unsafe_allow_html=True)

if not EXPLORER_DIR.exists() or not list(EXPLORER_DIR.glob("*.parquet")):
    st.error(
        "دیتای کاوشگر هنوز ساخته نشده است. "
        "ابتدا در ترمینال دستور `python prepare_explorer_data.py` را اجرا کنید."
    )
    st.stop()

try:
    ref = load_parquet("hs_reference.parquet")
    hs_maps = make_reference_maps(ref)
except Exception:
    ref = pd.DataFrame()
    hs_maps = {"HS2": {}, "HS4": {}, "HS6": {}, "HS8": {}}

def run_query(sql, params=None):
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
    clauses = [
        "Flow = ?",
        "Year BETWEEN ? AND ?",
    ]
    params = [flow, int(year_start), int(year_end)]

    def add_in(col, values):
        vals = [v for v in values if v not in (None, "")]
        if vals:
            clauses.append(
                f"{col} IN ({','.join(['?'] * len(vals))})"
            )
            params.extend(vals)

    add_in("Custom", customs)
    add_in("Country", countries)
    add_in("HS2", hs2)
    add_in("HS4", hs4)
    add_in("HS6", hs6)
    add_in("HS8", hs8)

    return " AND ".join(clauses), params

@st.cache_data(show_spinner=False)
def distinct_values(column, flow, year_start, year_end, customs=(), countries=(), hs2=(), hs4=(), hs6=()):
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

    df = run_query(
        f"""
        SELECT DISTINCT {column} AS value
        FROM read_parquet('{GLOB}')
        WHERE {where}
          AND {column} IS NOT NULL
          AND CAST({column} AS VARCHAR) <> ''
        ORDER BY value
        """,
        params,
    )
    return tuple(df["value"].astype(str).tolist())

years_df = run_query(
    f"""
    SELECT MIN(Year) AS min_year, MAX(Year) AS max_year
    FROM read_parquet('{GLOB}')
    """
)
min_year = int(years_df.iloc[0]["min_year"])
max_year = int(years_df.iloc[0]["max_year"])

# ---------------------------------------------------
# Filters
# ---------------------------------------------------
st.markdown('<div class="section-title">فیلترها</div>', unsafe_allow_html=True)

f1, f2 = st.columns([1, 2])
with f1:
    flow = st.radio(
        "جریان تجارت",
        ["صادرات", "واردات"],
        horizontal=True,
    )
with f2:
    year_range = st.slider(
        "بازه سال",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
    )

custom_options = distinct_values(
    "Custom",
    flow,
    year_range[0],
    year_range[1],
)
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
    )

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
    )

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
    )

where, params = where_sql(
    flow,
    year_range[0],
    year_range[1],
    customs=tuple(customs),
    countries=tuple(countries),
    hs2=tuple(hs2),
    hs4=tuple(hs4),
    hs6=tuple(hs6),
    hs8=tuple(hs8),
)

annual = run_query(
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
    FROM read_parquet('{GLOB}')
    WHERE {where}
    GROUP BY Year
    ORDER BY Year
    """,
    params,
)

if annual.empty:
    st.warning("هیچ رکوردی با ترکیب فیلترهای انتخاب‌شده پیدا نشد.")
    st.stop()

# ---------------------------------------------------
# KPI
# ---------------------------------------------------
st.divider()
st.markdown(
    '<div class="section-title">خلاصه انتخاب</div>',
    unsafe_allow_html=True,
)

total_dollar = annual["Dollar_Value"].sum()
total_rial = annual["Rial_Value"].sum()
total_weight = annual["Weight_kg"].sum()
overall_uv = (
    total_dollar / (total_weight / 1000.0)
    if total_weight > 0 else None
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("ارزش دلاری در کل دوره", f"{total_dollar/1e9:,.2f} میلیارد دلار")
k2.metric("ارزش ریالی در کل دوره", f"{total_rial/1e12:,.2f} هزار میلیارد ریال")
k3.metric("وزن در کل دوره", f"{total_weight/1e9:,.2f} میلیون تن")
k4.metric(
    "ارزش هر تن در کل دوره",
    "—" if overall_uv is None else f"{overall_uv:,.0f} دلار/تن",
)

# ---------------------------------------------------
# Trends
# ---------------------------------------------------
st.markdown(
    '<div class="section-title">روند سالانه</div>',
    unsafe_allow_html=True,
)

tab_d, tab_r, tab_w, tab_u = st.tabs(
    ["ارزش دلاری", "ارزش ریالی", "وزن", "ارزش هر تن"]
)

with tab_d:
    fig = px.line(
        annual.assign(Value=annual["Dollar_Value"]/1e9),
        x="Year",
        y="Value",
        markers=True,
        labels={"Year":"سال","Value":"میلیارد دلار"},
    )
    fig.update_layout(title="روند ارزش دلاری")
    fig = chart_layout(fig, height=460, y_title="میلیارد دلار")
    st.plotly_chart(fig, use_container_width=True)

with tab_r:
    fig = px.line(
        annual.assign(Value=annual["Rial_Value"]/1e12),
        x="Year",
        y="Value",
        markers=True,
        labels={"Year":"سال","Value":"هزار میلیارد ریال"},
    )
    fig.update_layout(title="روند ارزش ریالی")
    fig = chart_layout(fig, height=460, y_title="هزار میلیارد ریال")
    st.plotly_chart(fig, use_container_width=True)

with tab_w:
    fig = px.line(
        annual.assign(Value=annual["Weight_kg"]/1e9),
        x="Year",
        y="Value",
        markers=True,
        labels={"Year":"سال","Value":"میلیون تن"},
    )
    fig.update_layout(title="روند وزن تجارت")
    fig = chart_layout(fig, height=460, y_title="میلیون تن")
    st.plotly_chart(fig, use_container_width=True)

with tab_u:
    fig = px.line(
        annual,
        x="Year",
        y="Unit_Value",
        markers=True,
        labels={"Year":"سال","Unit_Value":"دلار به ازای هر تن"},
    )
    fig.update_layout(title="روند ارزش هر تن")
    fig = chart_layout(fig, height=460, y_title="دلار به ازای هر تن")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------
# Table
# ---------------------------------------------------
st.markdown(
    '<div class="section-title">جدول سالانه انتخاب</div>',
    unsafe_allow_html=True,
)

table = annual.copy()
table["ارزش دلاری (میلیارد دلار)"] = table["Dollar_Value"]/1e9
table["ارزش ریالی (هزار میلیارد ریال)"] = table["Rial_Value"]/1e12
table["وزن (میلیون تن)"] = table["Weight_kg"]/1e9
table["ارزش هر تن (دلار)"] = table["Unit_Value"]

show = table[
    [
        "Year",
        "ارزش دلاری (میلیارد دلار)",
        "ارزش ریالی (هزار میلیارد ریال)",
        "وزن (میلیون تن)",
        "ارزش هر تن (دلار)",
    ]
].rename(columns={"Year":"سال"})

st.dataframe(
    show,
    use_container_width=True,
    hide_index=True,
)

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
if hs8:
    st.markdown(
        '<div class="section-title">شرح تعرفه‌های HS8 انتخاب‌شده</div>',
        unsafe_allow_html=True,
    )
    for code in hs8:
        st.write(f"**{label_for(code, 'HS8', hs_maps)}**")
