
import plotly.express as px
import streamlit as st
from page_utils import metric_card, horizontal_bar_layout, fix_year_axis

from data_utils import load_trade_table, fmt_pct
from page_utils import (
    metric_column, metric_scaled, chart_layout,
    top_share_cards, hhi_from_values, yoy_from_table, format_number
)

ir = load_trade_table("country_annual.parquet")
b = load_trade_table("bushehr_country_annual.parquet")

st.markdown("""
<div class="trade-hero">
  <div class="trade-hero-title">شرکای تجاری</div>
  <div class="trade-hero-subtitle">
    مقاصد صادراتی، مبادی وارداتی، تمرکز بازار و روند تجارت با کشورهای منتخب
  </div>
</div>
""", unsafe_allow_html=True)

years = sorted(int(x) for x in ir["Year"].dropna().unique())

c1,c2,c3,c4 = st.columns(4)
with c1:
    flow = st.radio("جریان تجارت", ["صادرات","واردات"], horizontal=True)
with c2:
    geography = st.selectbox(
        "جغرافیا",
        ["ایران", "بوشهر — بدون پارس جنوبی", "بوشهر — با پارس جنوبی"],
    )
with c3:
    metric = st.selectbox("معیار", ["ارزش دلاری","وزن"])
with c4:
    year = st.selectbox("سال منتخب", years, index=len(years)-1)

if geography == "ایران":
    df = ir[ir["Flow"].eq(flow)].copy()
    title_geo = "ایران"
else:
    mode = "بدون پارس جنوبی" if "بدون" in geography else "با پارس جنوبی"
    df = b[(b["Flow"].eq(flow)) & (b["Bushehr_Mode"].eq(mode))].copy()
    title_geo = geography.replace(" — "," ")

if flow == "صادرات" and year == 1394:
    st.warning("جزئیات کشور طرف معامله در منبع صادرات ۱۳۹۴ موجود نیست.")

value_col = metric_column(metric)
snap = (
    df[df["Year"].eq(year)]
    .dropna(subset=[value_col])
    .sort_values(value_col, ascending=False)
)

st.markdown(
    f'<div class="section-title">شرکای اصلی {flow} {title_geo} در سال {year}</div>',
    unsafe_allow_html=True,
)

top = snap.head(15).sort_values(value_col)
if not top.empty:
    xvals, xlab = metric_scaled(top[value_col], metric)
    fig = px.bar(
        top.assign(_x=xvals),
        x="_x", y="Country", orientation="h",
        labels={"_x":xlab,"Country":""},
    )
    fig = chart_layout(fig, height=610, hovermode="closest")
    fig = horizontal_bar_layout(fig, top["Country"])
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

s3,s5,s10 = top_share_cards(snap, value_col=value_col)
hhi = hhi_from_values(snap[value_col])
m1,m2,m3,m4 = st.columns(4)
metric_card(m1, "سهم ۳ شریک نخست", fmt_pct(s3))
metric_card(m2, "سهم ۵ شریک نخست", fmt_pct(s5))
metric_card(m3, "سهم ۱۰ شریک نخست", fmt_pct(s10))
metric_card(m4, "شاخص HHI", "—" if hhi is None else f"{hhi:,.0f}")

st.divider()
st.markdown('<div class="section-title">روند تجارت با کشورهای منتخب</div>', unsafe_allow_html=True)

all_countries = sorted(df["Country"].dropna().unique())
default = snap.head(5)["Country"].dropna().tolist()
selected = st.multiselect("کشورها", all_countries, default=default)

trend = df[df["Country"].isin(selected)].copy()
if not trend.empty:
    vals, lab = metric_scaled(trend[value_col], metric)
    trend["_y"] = vals
    fig_t = px.line(
        trend, x="Year", y="_y", color="Country", markers=True,
        labels={"Year":"سال","_y":lab,"Country":""},
    )
    fig_t = chart_layout(fig_t, height=470, y_title=lab)
    fig_t = fix_year_axis(fig_t, trend["Year"])
    st.plotly_chart(fig_t, use_container_width=True)

st.divider()
st.markdown('<div class="section-title">پروفایل یک شریک تجاری</div>', unsafe_allow_html=True)

if all_countries:
    profile = st.selectbox("کشور", all_countries)
    p = df[(df["Country"].eq(profile)) & (df["Year"].eq(year))]
    ph = df[df["Country"].eq(profile)]
    if not p.empty:
        row = p.iloc[0]
        total_year = snap[value_col].sum()
        share = 100 * row[value_col]/total_year if total_year else None
        growth = yoy_from_table(ph, year, value_col=value_col)
        c1,c2,c3,c4 = st.columns(4)
        metric_card(c1, metric, format_number(row[value_col], metric))
        metric_card(c2, "سهم از کل", fmt_pct(share))
        metric_card(c3, "رشد سالانه", fmt_pct(growth))
        metric_card(c4, "ارزش هر تن", format_number(row.get("Unit_Value"), "ارزش هر تن"))
