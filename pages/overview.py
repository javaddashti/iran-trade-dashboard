from persian_display import fa_digits, persianize_figure
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from page_utils import (
    metric_card, chart_layout, horizontal_bar_layout, fix_year_axis,
)

from data_utils import (
    load_parquet,
    yoy_pct,
    fmt_usd_billion,
    fmt_million_ton,
    fmt_pct,
    fmt_usd_per_ton,
)

# ---------------------------
# Load processed annual data
# ---------------------------
try:
    national = load_parquet("national_annual.parquet")
    bushehr = load_parquet("bushehr_annual.parquet")
    bushehr_country = load_parquet("bushehr_country_annual.parquet")
    bushehr_hs2 = load_parquet("bushehr_hs2_annual.parquet")
except FileNotFoundError as e:
    st.error(str(e))
    st.info(
        "ابتدا فایل‌های export-all.dta و import-all.dta را داخل data/raw قرار دهید "
        "و سپس در ترمینال دستور `python prepare_data.py` را اجرا کنید."
    )
    st.stop()

# ---------------------------
# Helpers
# ---------------------------
def selected_value(df, year, flow, col):
    x = df[(df["Year"] == year) & (df["Flow"] == flow)]
    if x.empty:
        return float("nan")
    return x[col].sum()

def prior_value(df, year, flow, col):
    return selected_value(df, year - 1, flow, col)

def trade_balance(df, year):
    exp = selected_value(df, year, "صادرات", "Dollar_Value")
    imp = selected_value(df, year, "واردات", "Dollar_Value")
    return exp - imp

def unit_value(value, weight_kg):
    if weight_kg is None or pd.isna(weight_kg) or weight_kg <= 0:
        return float("nan")
    return value / (weight_kg / 1000.0)

# ---------------------------
# Hero
# ---------------------------
st.markdown(
    """
    <div class="trade-hero">
        <div class="trade-hero-title">داشبورد تجارت خارجی ایران و بوشهر</div>
        <div class="trade-hero-subtitle">
            نمای سالانه تجارت گمرکی کشور و جایگاه بوشهر | دوره ۱۳۹۰ تا ۱۴۰۳
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

years = sorted(int(x) for x in national["Year"].dropna().unique())
default_year = max(years)

c1, c2 = st.columns([1, 1])
with c1:
    selected_year = st.selectbox(
        "سال منتخب",
        options=years,
        index=len(years) - 1,
        format_func=fa_digits,
    )
with c2:
    bushehr_mode = st.radio(
        "تعریف بوشهر",
        options=["بدون پارس جنوبی", "با پارس جنوبی"],
        horizontal=True,
        index=0,
    )

bdf = bushehr[bushehr["Bushehr_Mode"] == bushehr_mode].copy()

# ---------------------------
# National overview
# ---------------------------
st.markdown(
    '<div class="section-kicker">تصویر کلان</div>'
    '<div class="section-title">تجارت خارجی ایران</div>',
    unsafe_allow_html=True,
)

exp = selected_value(national, selected_year, "صادرات", "Dollar_Value")
imp = selected_value(national, selected_year, "واردات", "Dollar_Value")
bal = exp - imp
total = exp + imp

exp_prev = prior_value(national, selected_year, "صادرات", "Dollar_Value")
imp_prev = prior_value(national, selected_year, "واردات", "Dollar_Value")
bal_prev = trade_balance(national, selected_year - 1) if selected_year - 1 in years else None
total_prev = (
    prior_value(national, selected_year, "صادرات", "Dollar_Value")
    + prior_value(national, selected_year, "واردات", "Dollar_Value")
)

k1, k2, k3, k4 = st.columns(4)
metric_card(k1, "صادرات", fmt_usd_billion(exp), fmt_pct(yoy_pct(exp, exp_prev)))
metric_card(k2, "واردات", fmt_usd_billion(imp), fmt_pct(yoy_pct(imp, imp_prev)))
metric_card(k3, 
    "تراز تجاری",
    fmt_usd_billion(bal),
    None if bal_prev is None else f"{(bal-bal_prev)/1e9:+,.1f} میلیارد دلار",
)
metric_card(k4, "حجم کل تجارت", fmt_usd_billion(total), fmt_pct(yoy_pct(total, total_prev)))

trend = (
    national.pivot_table(
        index="Year",
        columns="Flow",
        values="Dollar_Value",
        aggfunc="sum",
    )
    .reset_index()
    .sort_values("Year")
)
trend["تراز تجاری"] = trend.get("صادرات", 0) - trend.get("واردات", 0)

fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=trend["Year"],
        y=trend["صادرات"] / 1e9,
        mode="lines+markers",
        name="صادرات",
    )
)
fig.add_trace(
    go.Scatter(
        x=trend["Year"],
        y=trend["واردات"] / 1e9,
        mode="lines+markers",
        name="واردات",
    )
)
fig.add_trace(
    go.Bar(
        x=trend["Year"],
        y=trend["تراز تجاری"] / 1e9,
        name="تراز تجاری",
        opacity=0.32,
    )
)
fig = chart_layout(fig, height=470, y_title="میلیارد دلار")
fig = fix_year_axis(fig, trend["Year"])
fig.update_layout(title="روند صادرات، واردات و تراز تجاری ایران")
st.plotly_chart(
        persianize_figure(fig), use_container_width=True)

st.divider()

# ---------------------------
# Bushehr KPIs
# ---------------------------
st.markdown(
    '<div class="section-kicker">تمرکز استانی</div>'
    f'<div class="section-title">بوشهر در یک نگاه — {bushehr_mode}</div>',
    unsafe_allow_html=True,
)

b_exp = selected_value(bdf, selected_year, "صادرات", "Dollar_Value")
b_imp = selected_value(bdf, selected_year, "واردات", "Dollar_Value")
b_bal = b_exp - b_imp

b_exp_prev = prior_value(bdf, selected_year, "صادرات", "Dollar_Value")
b_imp_prev = prior_value(bdf, selected_year, "واردات", "Dollar_Value")

share_exp = 100 * b_exp / exp if exp else float("nan")
share_imp = 100 * b_imp / imp if imp else float("nan")

bk1, bk2, bk3, bk4, bk5 = st.columns(5)
metric_card(bk1, "صادرات بوشهر", fmt_usd_billion(b_exp), fmt_pct(yoy_pct(b_exp, b_exp_prev)))
metric_card(bk2, "واردات بوشهر", fmt_usd_billion(b_imp), fmt_pct(yoy_pct(b_imp, b_imp_prev)))
metric_card(bk3, "تراز تجاری بوشهر", fmt_usd_billion(b_bal))
metric_card(bk4, "سهم از صادرات ایران", fmt_pct(share_exp))
metric_card(bk5, "سهم از واردات ایران", fmt_pct(share_imp))

# ---------------------------
# Bushehr share trend
# ---------------------------
bn = bdf.merge(
    national,
    on=["Year", "Flow"],
    suffixes=("_b", "_ir"),
    how="left",
)
bn["Share"] = 100 * bn["Dollar_Value_b"] / bn["Dollar_Value_ir"]

share_pivot = (
    bn.pivot_table(index="Year", columns="Flow", values="Share", aggfunc="sum")
      .reset_index()
      .sort_values("Year")
)

fig_share = go.Figure()
for flow in ["صادرات", "واردات"]:
    if flow in share_pivot.columns:
        fig_share.add_trace(
            go.Scatter(
                x=share_pivot["Year"],
                y=share_pivot[flow],
                mode="lines+markers",
                name=flow,
            )
        )
fig_share = chart_layout(fig_share, height=410, y_title="درصد از کل کشور")
fig_share = fix_year_axis(fig_share, share_pivot["Year"])
fig_share.update_layout(title="سهم بوشهر از تجارت گمرکی کشور")
st.plotly_chart(
        persianize_figure(fig_share), use_container_width=True)

# ---------------------------
# Value / Weight / Unit value
# ---------------------------
st.markdown(
    '<div class="section-title">ارزش، وزن و ارزش واحد تجارت بوشهر</div>',
    unsafe_allow_html=True,
)

display_metric = st.radio(
    "معیار نمودار",
    ["ارزش دلاری", "وزن", "ارزش هر تن"],
    horizontal=True,
    key="overview_bushehr_metric",
)

bp = (
    bdf.pivot_table(
        index="Year",
        columns="Flow",
        values=["Dollar_Value", "Weight_kg"],
        aggfunc="sum",
    )
    .sort_index()
)

if display_metric == "ارزش دلاری":
    fig_metric = go.Figure()
    for flow_name in ["صادرات", "واردات"]:
        if ("Dollar_Value", flow_name) in bp.columns:
            fig_metric.add_trace(
                go.Scatter(
                    x=bp.index,
                    y=bp[("Dollar_Value", flow_name)] / 1e9,
                    mode="lines+markers",
                    name=flow_name,
                )
            )
    fig_metric = chart_layout(fig_metric, height=410, y_title="میلیارد دلار")
    fig_metric = fix_year_axis(fig_metric, bp.index)
    st.plotly_chart(
        persianize_figure(fig_metric), use_container_width=True)

elif display_metric == "وزن":
    fig_metric = go.Figure()
    for flow_name in ["صادرات", "واردات"]:
        if ("Weight_kg", flow_name) in bp.columns:
            fig_metric.add_trace(
                go.Scatter(
                    x=bp.index,
                    y=bp[("Weight_kg", flow_name)] / 1e9,
                    mode="lines+markers",
                    name=flow_name,
                )
            )
    fig_metric = chart_layout(fig_metric, height=410, y_title="میلیون تن")
    fig_metric = fix_year_axis(fig_metric, bp.index)
    st.plotly_chart(
        persianize_figure(fig_metric), use_container_width=True)

else:
    unit = pd.DataFrame(index=bp.index)
    for flow_name in ["صادرات", "واردات"]:
        if ("Dollar_Value", flow_name) in bp.columns and ("Weight_kg", flow_name) in bp.columns:
            denom = bp[("Weight_kg", flow_name)] / 1000.0
            unit[flow_name] = bp[("Dollar_Value", flow_name)].where(denom.gt(0)) / denom.where(denom.gt(0))

    selected_u_exp = unit.loc[selected_year, "صادرات"] if selected_year in unit.index and "صادرات" in unit.columns else float("nan")
    selected_u_imp = unit.loc[selected_year, "واردات"] if selected_year in unit.index and "واردات" in unit.columns else float("nan")
    ratio = 100 * selected_u_exp / selected_u_imp if selected_u_imp and not pd.isna(selected_u_imp) else float("nan")

    uc1, uc2, uc3 = st.columns(3)
    metric_card(uc1, "ارزش هر تن صادرات", fmt_usd_per_ton(selected_u_exp))
    metric_card(uc2, "ارزش هر تن واردات", fmt_usd_per_ton(selected_u_imp))
    metric_card(uc3, "نسبت ارزش واحد صادرات به واردات", fmt_pct(ratio))

    fig_metric = go.Figure()
    for flow_name in ["صادرات", "واردات"]:
        if flow_name in unit.columns:
            fig_metric.add_trace(
                go.Scatter(
                    x=unit.index,
                    y=unit[flow_name],
                    mode="lines+markers",
                    name=flow_name,
                )
            )
    fig_metric = chart_layout(fig_metric, height=410, y_title="دلار به ازای هر تن")
    fig_metric = fix_year_axis(fig_metric, bp.index)
    st.plotly_chart(
        persianize_figure(fig_metric), use_container_width=True)

st.divider()

# ---------------------------
# Bushehr structure snapshot
# ---------------------------
st.markdown(
    f'<div class="section-title">ساختار تجارت بوشهر در سال {fa_digits(selected_year)}</div>',
    unsafe_allow_html=True,
)

flow_choice = st.radio(
    "جریان تجارت برای رتبه‌بندی",
    ["صادرات", "واردات"],
    horizontal=True,
    key="structure_flow",
)

structure_view = st.radio(
    "نوع رتبه‌بندی",
    ["شرکای تجاری", "گروه‌های کالایی HS2"],
    horizontal=True,
    key="overview_structure_view",
)

if structure_view == "شرکای تجاری":
    if selected_year == 1394 and flow_choice == "صادرات":
        st.warning(
            "در منبع صادرات سال ۱۳۹۴ که در کد پاک‌سازی استفاده شده، "
            "جزئیات کشور طرف معامله وجود ندارد؛ بنابراین رتبه‌بندی شرکا برای این سال کامل نیست."
        )

    x = bushehr_country[
        (bushehr_country["Year"] == selected_year)
        & (bushehr_country["Flow"] == flow_choice)
        & (bushehr_country["Bushehr_Mode"] == bushehr_mode)
    ].copy()

    x = x.sort_values("Dollar_Value", ascending=False)
    total_x = x["Dollar_Value"].sum()
    top = x.head(10).sort_values("Dollar_Value")

    if top.empty:
        st.info("برای این انتخاب داده‌ای در دسترس نیست.")
    else:
        fig_c = px.bar(
            top,
            x=top["Dollar_Value"] / 1e9,
            y="Country",
            orientation="h",
            labels={"x": "میلیارد دلار", "Country": ""},
        )
        fig_c.update_layout(title=f"۱۰ شریک اصلی {flow_choice} بوشهر")
        fig_c = chart_layout(fig_c, height=500, y_title=None)
        fig_c = horizontal_bar_layout(fig_c, top["Country"])
        fig_c.update_layout(showlegend=False, hovermode="closest")
        st.plotly_chart(
        persianize_figure(fig_c), use_container_width=True)

        m1, m2, m3 = st.columns(3)
        metric_card(m1, "سهم ۳ شریک نخست", fmt_pct(100 * x.head(3)["Dollar_Value"].sum() / total_x if total_x else None))
        metric_card(m2, "سهم ۵ شریک نخست", fmt_pct(100 * x.head(5)["Dollar_Value"].sum() / total_x if total_x else None))
        metric_card(m3, "سهم ۱۰ شریک نخست", fmt_pct(100 * x.head(10)["Dollar_Value"].sum() / total_x if total_x else None))

else:
    if selected_year == 1394 and flow_choice == "صادرات":
        st.warning(
            "در منبع صادرات سال ۱۳۹۴ که در کد پاک‌سازی استفاده شده، "
            "جزئیات کد تعرفه وجود ندارد؛ بنابراین ترکیب کالایی این سال کامل نیست."
        )

    h = bushehr_hs2[
        (bushehr_hs2["Year"] == selected_year)
        & (bushehr_hs2["Flow"] == flow_choice)
        & (bushehr_hs2["Bushehr_Mode"] == bushehr_mode)
    ].copy()

    if "HS2_desc" in h.columns:
        h["Label"] = h["HS2"].astype(str) + " — " + h["HS2_desc"].fillna("بدون عنوان")
    else:
        h["Label"] = "HS " + h["HS2"].astype(str)

    h = h.sort_values("Dollar_Value", ascending=False)
    total_h = h["Dollar_Value"].sum()
    top_h = h.head(10).sort_values("Dollar_Value")

    if top_h.empty:
        st.info("برای این انتخاب داده‌ای در دسترس نیست.")
    else:
        fig_h = px.bar(
            top_h,
            x=top_h["Dollar_Value"] / 1e9,
            y="Label",
            orientation="h",
            labels={"x": "میلیارد دلار", "Label": ""},
        )
        fig_h.update_layout(title=f"۱۰ گروه کالایی اصلی {flow_choice} بوشهر")
        fig_h = chart_layout(fig_h, height=560, y_title=None)
        fig_h = horizontal_bar_layout(fig_h, top_h["Label"], long=True)
        fig_h.update_layout(showlegend=False, hovermode="closest")
        st.plotly_chart(
        persianize_figure(fig_h), use_container_width=True)

        hm1, hm2, hm3 = st.columns(3)
        metric_card(hm1, "سهم ۳ گروه نخست", fmt_pct(100 * h.head(3)["Dollar_Value"].sum() / total_h if total_h else None))
        metric_card(hm2, "سهم ۵ گروه نخست", fmt_pct(100 * h.head(5)["Dollar_Value"].sum() / total_h if total_h else None))
        metric_card(hm3, "سهم ۱۰ گروه نخست", fmt_pct(100 * h.head(10)["Dollar_Value"].sum() / total_h if total_h else None))

st.caption(
    "یادآوری: ارقام «بوشهر» در این داشبورد، تجارت ثبت‌شده در گمرک‌های تعریف‌شده برای بوشهر را نشان می‌دهد "
    "و لزوماً معادل محل تولید کالای صادراتی یا محل مصرف نهایی کالای وارداتی نیست."
)
