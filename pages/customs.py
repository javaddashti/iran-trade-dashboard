
import plotly.express as px
import streamlit as st

from data_utils import load_parquet, load_trade_table, fmt_pct
from page_utils import (
    metric_column, metric_scaled, chart_layout,
    top_share_cards, hhi_from_values, yoy_from_table, format_number
)

df_all = load_trade_table("custom_annual.parquet")
nat = load_parquet("national_annual.parquet")

st.markdown("""
<div class="trade-hero">
  <div class="trade-hero-title">گمرک‌ها و بنادر</div>
  <div class="trade-hero-subtitle">
    رتبه‌بندی مبادی گمرکی، تمرکز تجارت، روند سهم و مقایسه عملکرد گمرک‌ها
  </div>
</div>
""", unsafe_allow_html=True)

years = sorted(int(x) for x in df_all["Year"].dropna().unique())

c1,c2,c3 = st.columns(3)
with c1:
    flow = st.radio("جریان تجارت", ["صادرات","واردات"], horizontal=True)
with c2:
    metric = st.selectbox("معیار", ["ارزش دلاری","وزن","ارزش هر تن"])
with c3:
    year = st.selectbox("سال منتخب", years, index=len(years)-1)

df = df_all[df_all["Flow"].eq(flow)].copy()
value_col = metric_column(metric)
snap = (
    df[df["Year"].eq(year)]
    .dropna(subset=[value_col])
    .sort_values(value_col, ascending=False)
)

st.markdown(
    f'<div class="section-title">رتبه‌بندی گمرک‌ها در {flow} سال {year}</div>',
    unsafe_allow_html=True,
)

top = snap.head(20).sort_values(value_col)
if not top.empty:
    xvals, xlab = metric_scaled(top[value_col], metric)
    fig = px.bar(
        top.assign(_x=xvals),
        x="_x", y="Custom", orientation="h",
        labels={"_x":xlab,"Custom":""},
    )
    fig = chart_layout(fig, height=680, hovermode="closest")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

s3,s5,s10 = top_share_cards(snap, value_col=value_col)
hhi = hhi_from_values(snap[value_col])
a,b,c,d = st.columns(4)
a.metric("سهم ۳ گمرک نخست", fmt_pct(s3))
b.metric("سهم ۵ گمرک نخست", fmt_pct(s5))
c.metric("سهم ۱۰ گمرک نخست", fmt_pct(s10))
d.metric("شاخص HHI", "—" if hhi is None else f"{hhi:,.0f}")

st.divider()
st.markdown('<div class="section-title">مقایسه روند گمرک‌های منتخب</div>', unsafe_allow_html=True)

all_customs = sorted(df["Custom"].dropna().unique())
default = snap.head(5)["Custom"].dropna().tolist()
selected = st.multiselect("گمرک‌ها", all_customs, default=default)

trend = df[df["Custom"].isin(selected)].copy()
if not trend.empty:
    vals, lab = metric_scaled(trend[value_col], metric)
    trend["_y"] = vals
    fig_t = px.line(
        trend, x="Year", y="_y", color="Custom", markers=True,
        labels={"Year":"سال","_y":lab,"Custom":""},
    )
    fig_t = chart_layout(fig_t, height=500, y_title=lab)
    st.plotly_chart(fig_t, use_container_width=True)

st.divider()
st.markdown('<div class="section-title">ارزش در برابر وزن گمرک‌ها</div>', unsafe_allow_html=True)
st.caption("برای شناسایی گمرک‌های حجیم اما کم‌ارزش‌تر و گمرک‌های کم‌وزن اما با ارزش بالاتر.")

scatter = snap[(snap["Dollar_Value"]>0) & (snap["Weight_kg"]>0)].copy()
scatter["Value_bn"] = scatter["Dollar_Value"]/1e9
scatter["Weight_mt"] = scatter["Weight_kg"]/1e9

if not scatter.empty:
    fig_s = px.scatter(
        scatter,
        x="Weight_mt", y="Value_bn",
        hover_name="Custom",
        labels={"Weight_mt":"وزن (میلیون تن)","Value_bn":"ارزش (میلیارد دلار)"},
    )
    fig_s = chart_layout(fig_s, height=520, y_title="میلیارد دلار", hovermode="closest")
    st.plotly_chart(fig_s, use_container_width=True)

st.divider()
st.markdown('<div class="section-title">پروفایل یک گمرک</div>', unsafe_allow_html=True)

if all_customs:
    profile = st.selectbox("گمرک", all_customs)
    p = df[(df["Custom"].eq(profile)) & (df["Year"].eq(year))]
    ph = df[df["Custom"].eq(profile)]
    if not p.empty:
        row = p.iloc[0]
        nat_year = nat[(nat["Year"].eq(year)) & (nat["Flow"].eq(flow))]["Dollar_Value"].sum()
        share = 100*row["Dollar_Value"]/nat_year if nat_year else None
        growth = yoy_from_table(ph, year, value_col="Dollar_Value")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("ارزش تجارت", format_number(row["Dollar_Value"], "ارزش دلاری"))
        c2.metric("سهم از کل کشور", fmt_pct(share))
        c3.metric("رشد ارزش سالانه", fmt_pct(growth))
        c4.metric("ارزش هر تن", format_number(row.get("Unit_Value"), "ارزش هر تن"))

st.caption(
    "گمرک محل ثبت تجارت است و لزوماً محل تولید کالای صادراتی یا مصرف نهایی کالای وارداتی نیست."
)
