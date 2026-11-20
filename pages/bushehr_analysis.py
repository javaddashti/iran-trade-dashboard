from persian_display import fa_digits, persianize_figure

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from page_utils import metric_card, horizontal_bar_layout, fix_year_axis

from data_utils import (
    load_trade_table,
    load_hs_reference_bundle,
    fmt_pct,
    fmt_usd_billion,
)
from page_utils import (
    chart_layout,
    top_share_cards,
)
from hs_helpers import (
    label_for,
    short_label_for,
)

nat = load_trade_table("national_annual.parquet")
b = load_trade_table("bushehr_annual.parquet")
bc = load_trade_table("bushehr_country_annual.parquet")

hs_ir = load_trade_table("hs_hierarchy_national.parquet")
hs_b = load_trade_table("hs_hierarchy_bushehr.parquet")

ref, maps = load_hs_reference_bundle()

st.markdown(
    """
    <div class="trade-hero">
      <div class="trade-hero-title">تحلیل بوشهر</div>
      <div class="trade-hero-subtitle">
        جایگاه بوشهر در تجارت کشور، کیفیت سبد صادرات، تمرکز بازار و تخصص‌یافتگی کالایی
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

years = sorted(
    int(x)
    for x in nat["Year"].dropna().unique()
)

c1, c2 = st.columns(2)

with c1:
    mode = st.radio(
        "تعریف بوشهر",
        [
            "بدون پارس جنوبی",
            "با پارس جنوبی",
        ],
        horizontal=True,
    )

with c2:
    year = st.selectbox(
        "سال منتخب",
        years,
        index=len(years) - 1,
        format_func=fa_digits,
    )

bd = b[
    b["Bushehr_Mode"].eq(mode)
].copy()


def val(df, y, flow, col="Dollar_Value"):
    z = df[
        df["Year"].eq(y)
        & df["Flow"].eq(flow)
    ]

    return (
        z[col].sum()
        if not z.empty
        else 0
    )


be = val(bd, year, "صادرات")
bi = val(bd, year, "واردات")
ie = val(nat, year, "صادرات")
ii = val(nat, year, "واردات")

k1, k2, k3, k4, k5 = st.columns(5)

metric_card(k1, 
    "صادرات بوشهر",
    fmt_usd_billion(be),
)
metric_card(k2, 
    "واردات بوشهر",
    fmt_usd_billion(bi),
)
metric_card(k3, 
    "تراز بوشهر",
    fmt_usd_billion(be - bi),
)
metric_card(k4, 
    "سهم از صادرات ایران",
    fmt_pct(
        100 * be / ie
        if ie
        else None
    ),
)
metric_card(k5, 
    "سهم از واردات ایران",
    fmt_pct(
        100 * bi / ii
        if ii
        else None
    ),
)

bn = bd.merge(
    nat,
    on=["Year", "Flow"],
    suffixes=("_B", "_IR"),
    how="left",
)

bn["Share"] = (
    100
    * bn["Dollar_Value_B"]
    / bn["Dollar_Value_IR"]
)

fig_share = px.line(
    bn,
    x="Year",
    y="Share",
    color="Flow",
    markers=True,
    labels={
        "Year": "سال",
        "Share": "درصد از کل کشور",
        "Flow": "",
    },
)

fig_share.update_layout(
    title="سهم بوشهر از صادرات و واردات کشور"
)

fig_share = chart_layout(fig_share, height=450, y_title="درصد از کل کشور")
fig_share = fix_year_axis(fig_share, bn["Year"])

st.plotly_chart(
        persianize_figure(fig_share),
    use_container_width=True,
)

st.markdown(
    '<div class="section-title">ارزش هر تن؛ بوشهر در برابر ایران</div>',
    unsafe_allow_html=True,
)

uv_flow = st.radio(
    "جریان",
    ["صادرات", "واردات"],
    horizontal=True,
    key="uv_flow",
)

buv = (
    bd[
        bd["Flow"].eq(uv_flow)
    ][["Year", "Unit_Value"]]
    .rename(
        columns={
            "Unit_Value": "بوشهر"
        }
    )
)

iuv = (
    nat[
        nat["Flow"].eq(uv_flow)
    ][["Year", "Unit_Value"]]
    .rename(
        columns={
            "Unit_Value": "ایران"
        }
    )
)

uv = buv.merge(
    iuv,
    on="Year",
    how="outer",
).sort_values("Year")

fig_uv = go.Figure()

fig_uv.add_trace(
    go.Scatter(
        x=uv["Year"],
        y=uv["بوشهر"],
        mode="lines+markers",
        name="بوشهر",
    )
)

fig_uv.add_trace(
    go.Scatter(
        x=uv["Year"],
        y=uv["ایران"],
        mode="lines+markers",
        name="ایران",
    )
)

fig_uv.update_layout(
    title=f"ارزش هر تن {uv_flow}"
)

fig_uv = chart_layout(fig_uv, height=450, y_title="دلار به ازای هر تن")
fig_uv = fix_year_axis(fig_uv, uv["Year"])

st.plotly_chart(
        persianize_figure(fig_uv),
    use_container_width=True,
)

st.divider()

st.markdown(
    f'<div class="section-title">تمرکز صادرات بوشهر در سال {fa_digits(year)}</div>',
    unsafe_allow_html=True,
)

c = bc[
    bc["Year"].eq(year)
    & bc["Flow"].eq("صادرات")
    & bc["Bushehr_Mode"].eq(mode)
].copy()

h2 = hs_b[
    hs_b["Year"].eq(year)
    & hs_b["Flow"].eq("صادرات")
    & hs_b["Bushehr_Mode"].eq(mode)
    & hs_b["HS_Level"].eq("HS2")
].copy()

cs = (
    top_share_cards(
        c,
        "Dollar_Value",
    )
    if not c.empty
    else [None, None, None]
)

hs = (
    top_share_cards(
        h2,
        "Dollar_Value",
    )
    if not h2.empty
    else [None, None, None]
)

a, b1, c1 = st.columns(3)

metric_card(a, 
    "۳ مقصد نخست",
    fmt_pct(cs[0]),
)
metric_card(b1, 
    "۵ مقصد نخست",
    fmt_pct(cs[1]),
)
metric_card(c1, 
    "۱۰ مقصد نخست",
    fmt_pct(cs[2]),
)

d, e, f = st.columns(3)

metric_card(d, 
    "۳ گروه HS2 نخست",
    fmt_pct(hs[0]),
)
metric_card(e, 
    "۵ گروه HS2 نخست",
    fmt_pct(hs[1]),
)
metric_card(f, 
    "۱۰ گروه HS2 نخست",
    fmt_pct(hs[2]),
)

# ---------------------------------------------------
# LQ
# ---------------------------------------------------
st.markdown(
    f'<div class="section-title">تخصص‌یافتگی صادراتی بوشهر در سال {fa_digits(year)}</div>',
    unsafe_allow_html=True,
)

lq_level = st.selectbox(
    "سطح محاسبه LQ",
    ["HS2", "HS4", "HS6", "HS8"],
    index=0,
    format_func=fa_digits,
)

min_share = st.select_slider(
    "حداقل سهم کالا از صادرات بوشهر برای ورود به رتبه‌بندی",
    options=[round(i / 10.0, 1) for i in range(21)],
    value=0.1,
    format_func=lambda x: fa_digits(f"{x:.1f}٪"),
)

bb = hs_b[
    hs_b["Year"].eq(year)
    & hs_b["Flow"].eq("صادرات")
    & hs_b["Bushehr_Mode"].eq(mode)
    & hs_b["HS_Level"].eq(lq_level)
][
    ["HS_Code", "Dollar_Value"]
].rename(
    columns={
        "Dollar_Value": "B"
    }
)

ii_hs = hs_ir[
    hs_ir["Year"].eq(year)
    & hs_ir["Flow"].eq("صادرات")
    & hs_ir["HS_Level"].eq(lq_level)
][
    ["HS_Code", "Dollar_Value"]
].rename(
    columns={
        "Dollar_Value": "IR"
    }
)

lq = bb.merge(
    ii_hs,
    on="HS_Code",
    how="left",
)

btot = bb["B"].sum()
irtot = ii_hs["IR"].sum()

lq["B_share"] = (
    lq["B"] / btot
    if btot
    else pd.NA
)

lq["IR_share"] = (
    lq["IR"] / irtot
    if irtot
    else pd.NA
)

lq["LQ"] = (
    lq["B_share"]
    / lq["IR_share"]
)

lq = lq[
    (lq["B_share"] >= min_share / 100)
    & lq["LQ"].notna()
    & lq["LQ"]
      .replace(
          [
              float("inf"),
              -float("inf"),
          ],
          pd.NA,
      )
      .notna()
].copy()

lq = lq.nlargest(15, "LQ").copy()
lq["Full_Label"] = lq["HS_Code"].map(
    lambda x: label_for(x, lq_level, maps)
)
lq["Display"] = lq["HS_Code"].map(
    lambda x: short_label_for(x, lq_level, maps, max_chars=92)
)
lq = lq.sort_values("LQ")

if not lq.empty:
    fig_lq = px.bar(
        lq,
        x="LQ",
        y="Display",
        orientation="h",
        labels={
            "LQ": "شاخص تخصص‌یافتگی",
            "Display": "",
        },
        hover_data={
            "Full_Label": True,
            "HS_Code": True,
        },
    )

    fig_lq.add_vline(
        x=1,
        line_dash="dash",
    )

    fig_lq = chart_layout(
        fig_lq,
        height=590,
        hovermode="closest",
    )

    fig_lq = horizontal_bar_layout(fig_lq, lq["Display"], long=True)
    fig_lq.update_layout(showlegend=False)

    fig_lq.update_yaxes(
        automargin=True,
    )

    st.plotly_chart(
        persianize_figure(fig_lq),
        use_container_width=True,
    )

# ---------------------------------------------------
# Main products
# ---------------------------------------------------
st.markdown(
    f'<div class="section-title">کالاهای اصلی صادراتی بوشهر در سال {fa_digits(year)}</div>',
    unsafe_allow_html=True,
)

detail_level = st.radio(
    "سطح نمایش",
    [
        "HS2",
        "HS4",
        "HS6",
        "HS8",
    ],
    horizontal=True,
    format_func=fa_digits,
)

detail = hs_b[
    hs_b["Year"].eq(year)
    & hs_b["Flow"].eq("صادرات")
    & hs_b["Bushehr_Mode"].eq(mode)
    & hs_b["HS_Level"].eq(detail_level)
].copy()

detail = detail.nlargest(15, "Dollar_Value").copy()
detail["Full_Label"] = detail["HS_Code"].map(
    lambda x: label_for(x, detail_level, maps)
)
detail["Display"] = detail["HS_Code"].map(
    lambda x: short_label_for(x, detail_level, maps, max_chars=94)
)
detail = detail.sort_values("Dollar_Value")

if not detail.empty:
    fig_d = px.bar(
        detail.assign(
            Value=(
                detail["Dollar_Value"]
                / 1e9
            )
        ),
        x="Value",
        y="Display",
        orientation="h",
        labels={
            "Value": "میلیارد دلار",
            "Display": "",
        },
        hover_data={
            "Full_Label": True,
            "HS_Code": True,
            "Weight_kg": ":,.0f",
        },
    )

    fig_d = chart_layout(
        fig_d,
        height=600,
        hovermode="closest",
    )

    fig_d = horizontal_bar_layout(fig_d, detail["Display"], long=True)
    fig_d.update_layout(showlegend=False)

    fig_d.update_yaxes(
        automargin=True,
    )

    st.plotly_chart(
        persianize_figure(fig_d),
        use_container_width=True,
    )

st.caption(
    "عنوان HS۴ و HS۶ از کتاب مقررات صادرات و واردات ۱۳۹۶ استخراج شده است. "
    "شرح HS۸ از مرجع dd.xlsx پروژه استفاده می‌شود و در نبود آن از کتاب ۱۳۹۶ تکمیل می‌شود."
)
