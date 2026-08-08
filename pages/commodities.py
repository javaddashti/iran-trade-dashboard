
import pandas as pd
import plotly.express as px
import streamlit as st

from data_utils import load_parquet, fmt_pct
from page_utils import (
    unit_value,
    metric_column,
    metric_scaled,
    chart_layout,
    format_number,
)
from hs_helpers import (
    make_reference_maps,
    label_for,
    short_label_for,
    deepest_selected,
    child_codes,
    description_for,
)

national = unit_value(
    load_parquet("hs_hierarchy_national.parquet")
)
bushehr = unit_value(
    load_parquet("hs_hierarchy_bushehr.parquet")
)
ref = load_parquet("hs_reference.parquet")
maps = make_reference_maps(ref)

st.markdown(
    """
    <div class="trade-hero">
      <div class="trade-hero-title">کالاها و تعرفه‌ها</div>
      <div class="trade-hero-subtitle">
        مرور سلسله‌مراتبی HS از فصل دو رقمی تا تعرفه هشت‌رقمی
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

years = sorted(
    int(x)
    for x in national["Year"].dropna().unique()
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    flow = st.radio(
        "جریان تجارت",
        ["صادرات", "واردات"],
        horizontal=True,
    )

with c2:
    geography = st.selectbox(
        "جغرافیا",
        [
            "ایران",
            "بوشهر — بدون پارس جنوبی",
            "بوشهر — با پارس جنوبی",
        ],
    )

with c3:
    year = st.selectbox(
        "سال منتخب",
        years,
        index=len(years) - 1,
    )

with c4:
    metric = st.selectbox(
        "معیار",
        ["ارزش دلاری", "وزن", "ارزش هر تن"],
    )

if geography == "ایران":
    df = national[
        national["Flow"].eq(flow)
    ].copy()
    geo_title = "ایران"
    mode = None
else:
    mode = (
        "بدون پارس جنوبی"
        if "بدون" in geography
        else "با پارس جنوبی"
    )

    df = bushehr[
        bushehr["Flow"].eq(flow)
        & bushehr["Bushehr_Mode"].eq(mode)
    ].copy()

    geo_title = geography.replace(" — ", " ")

if flow == "صادرات" and year == 1394:
    st.warning(
        "در منبع صادرات ۱۳۹۴ جزئیات تعرفه وجود ندارد؛ "
        "بنابراین تحلیل HS برای این سال کامل نیست."
    )

st.caption(
    "عناوین HS4 و HS6 بر اساس کتاب مقررات صادرات و واردات ۱۳۹۶ است. "
    "شرح HS8 از مرجع dd.xlsx پروژه استفاده می‌شود و در نبود آن از کتاب ۱۳۹۶ تکمیل می‌شود."
)

# ---------------------------------------------------
# 1) Ranking
# ---------------------------------------------------
st.markdown(
    '<div class="section-title">رتبه‌بندی کالاها در سطح انتخابی</div>',
    unsafe_allow_html=True,
)

r1, r2 = st.columns([1, 2])

with r1:
    level = st.selectbox(
        "سطح HS",
        ["HS2", "HS4", "HS6", "HS8"],
    )

with r2:
    st.caption(
        "HS2 تصویر کلی سبد کالا را می‌دهد؛ "
        "HS8 دقیق‌ترین تعرفه موجود در داده است."
    )

parent_hs2 = None
parent_hs4 = None
parent_hs6 = None

year_df = df[df["Year"].eq(year)].copy()

if level in ["HS4", "HS6", "HS8"]:
    hs2_codes = child_codes(year_df, "HS2")

    parent_hs2 = st.selectbox(
        "محدود به فصل HS2",
        options=[None] + hs2_codes,
        format_func=lambda x: (
            "همه فصل‌ها"
            if x is None
            else label_for(x, "HS2", maps)
        ),
        key="rank_hs2",
    )

if level in ["HS6", "HS8"] and parent_hs2:
    hs4_codes = child_codes(
        year_df,
        "HS4",
        parent_hs2,
    )

    parent_hs4 = st.selectbox(
        "محدود به HS4",
        options=[None] + hs4_codes,
        format_func=lambda x: (
            "همه HS4ها"
            if x is None
            else label_for(x, "HS4", maps)
        ),
        key="rank_hs4",
    )

if level == "HS8" and parent_hs4:
    hs6_codes = child_codes(
        year_df,
        "HS6",
        parent_hs4,
    )

    parent_hs6 = st.selectbox(
        "محدود به HS6",
        options=[None] + hs6_codes,
        format_func=lambda x: (
            "همه HS6ها"
            if x is None
            else label_for(x, "HS6", maps)
        ),
        key="rank_hs6",
    )

rank = year_df[
    year_df["HS_Level"].eq(level)
].copy()

prefix = (
    parent_hs6
    or parent_hs4
    or parent_hs2
)

if prefix:
    rank = rank[
        rank["HS_Code"]
        .astype(str)
        .str.startswith(str(prefix))
    ]

value_col = metric_column(metric)

rank = (
    rank
    .dropna(subset=[value_col])
    .sort_values(
        value_col,
        ascending=False,
    )
)

rank["Full_Label"] = (
    rank["HS_Code"]
    .astype(str)
    .map(
        lambda x: label_for(
            x,
            level,
            maps,
        )
    )
)

rank["Display"] = (
    rank["HS_Code"]
    .astype(str)
    .map(
        lambda x: short_label_for(
            x,
            level,
            maps,
            max_chars=92,
        )
    )
)

top_n = st.slider(
    "تعداد اقلام در نمودار",
    10,
    30,
    20,
    5,
)

top = (
    rank
    .head(top_n)
    .sort_values(value_col)
)

if top.empty:
    st.info(
        "برای این انتخاب داده‌ای در دسترس نیست."
    )
else:
    xvals, xlab = metric_scaled(
        top[value_col],
        metric,
    )

    fig = px.bar(
        top.assign(_x=xvals),
        x="_x",
        y="Display",
        orientation="h",
        labels={
            "_x": xlab,
            "Display": "",
        },
        hover_data={
            "Full_Label": True,
            "HS_Code": True,
            "Dollar_Value": ":,.0f",
            "Weight_kg": ":,.0f",
        },
    )

    fig.update_traces(
        hovertemplate=(
            "%{customdata[0]}"
            "<br>کد HS: %{customdata[1]}"
            "<br>ارزش دلاری: %{customdata[2]:,.0f}"
            "<br>وزن: %{customdata[3]:,.0f} کیلوگرم"
            "<extra></extra>"
        )
    )

    fig = chart_layout(
        fig,
        height=max(520, top_n * 31),
        hovermode="closest",
    )

    fig.update_layout(
        showlegend=False,
        margin=dict(
            l=48,
            r=48,
            t=66,
            b=38,
        ),
    )

    fig.update_yaxes(
        automargin=True,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

# ---------------------------------------------------
# 2) Drill-down
# ---------------------------------------------------
st.divider()

st.markdown(
    '<div class="section-title">کاوش سلسله‌مراتبی یک کالا</div>',
    unsafe_allow_html=True,
)

st.caption(
    "ابتدا فصل HS2 را انتخاب کنید و در صورت نیاز تا HS8 پایین بروید. "
    "نمودار روند بر اساس عمیق‌ترین سطح انتخاب‌شده ساخته می‌شود."
)

base = df.copy()

hs2_options = child_codes(
    base,
    "HS2",
)

d_hs2 = st.selectbox(
    "HS2 — فصل",
    options=hs2_options,
    format_func=lambda x: label_for(
        x,
        "HS2",
        maps,
    ),
    key="drill_hs2",
)

hs4_options = child_codes(
    base,
    "HS4",
    d_hs2,
)

d_hs4 = st.selectbox(
    "HS4",
    options=[None] + hs4_options,
    format_func=lambda x: (
        "همه HS4های این فصل"
        if x is None
        else label_for(
            x,
            "HS4",
            maps,
        )
    ),
    key="drill_hs4",
)

d_hs6 = None
d_hs8 = None

if d_hs4:
    hs6_options = child_codes(
        base,
        "HS6",
        d_hs4,
    )

    d_hs6 = st.selectbox(
        "HS6",
        options=[None] + hs6_options,
        format_func=lambda x: (
            "همه HS6های این گروه"
            if x is None
            else label_for(
                x,
                "HS6",
                maps,
            )
        ),
        key="drill_hs6",
    )

if d_hs6:
    hs8_options = child_codes(
        base,
        "HS8",
        d_hs6,
    )

    d_hs8 = st.selectbox(
        "HS8 — تعرفه دقیق",
        options=[None] + hs8_options,
        format_func=lambda x: (
            "همه تعرفه‌های HS8 این زیرگروه"
            if x is None
            else label_for(
                x,
                "HS8",
                maps,
            )
        ),
        key="drill_hs8",
    )

selected_level, selected_code = (
    deepest_selected(
        hs2=d_hs2,
        hs4=d_hs4,
        hs6=d_hs6,
        hs8=d_hs8,
    )
)

if selected_level and selected_code:
    selected = base[
        base["HS_Level"].eq(selected_level)
        & base["HS_Code"].astype(str).eq(
            str(selected_code)
        )
    ].sort_values("Year")

    selected_year_row = selected[
        selected["Year"].eq(year)
    ]

    st.markdown(
        f"### {label_for(selected_code, selected_level, maps)}"
    )

    desc = description_for(
        selected_code,
        selected_level,
        ref,
    )

    if desc:
        source_note = (
            "کتاب مقررات صادرات و واردات ۱۳۹۶"
            if selected_level in ("HS4", "HS6")
            else "مرجع HS پروژه"
        )

        st.info(
            f"شرح {selected_level}: {desc}\n\n"
            f"منبع عنوان: {source_note}"
        )

    if not selected_year_row.empty:
        row = selected_year_row.iloc[0]

        total_same_level = year_df[
            year_df["HS_Level"].eq(
                selected_level
            )
        ]["Dollar_Value"].sum()

        share = (
            100
            * row["Dollar_Value"]
            / total_same_level
            if total_same_level
            else None
        )

        k1, k2, k3, k4 = st.columns(4)

        k1.metric(
            "ارزش دلاری",
            format_number(
                row["Dollar_Value"],
                "ارزش دلاری",
            ),
        )

        k2.metric(
            "وزن",
            format_number(
                row["Weight_kg"],
                "وزن",
            ),
        )

        k3.metric(
            "ارزش هر تن",
            format_number(
                row["Unit_Value"],
                "ارزش هر تن",
            ),
        )

        k4.metric(
            "سهم از تجارت در همین سطح",
            fmt_pct(share),
        )

    trend_metric = st.radio(
        "معیار نمودار روند",
        [
            "ارزش دلاری",
            "وزن",
            "ارزش هر تن",
        ],
        horizontal=True,
        key="drill_trend_metric",
    )

    trend_col = metric_column(
        trend_metric
    )

    vals, ylab = metric_scaled(
        selected[trend_col],
        trend_metric,
    )

    fig_t = px.line(
        selected.assign(_y=vals),
        x="Year",
        y="_y",
        markers=True,
        labels={
            "Year": "سال",
            "_y": ylab,
        },
    )

    fig_t.update_layout(
        title=(
            f"روند {label_for(selected_code, selected_level, maps)}"
        )
    )

    fig_t = chart_layout(
        fig_t,
        height=470,
        y_title=ylab,
        hovermode="x unified",
    )

    fig_t.update_layout(
        showlegend=False,
    )

    st.plotly_chart(
        fig_t,
        use_container_width=True,
    )

st.caption(
    "ملاحظه طبقه‌بندی: عناوین HS4 و HS6 بر اساس کتاب مقررات صادرات و واردات ۱۳۹۶ هستند. "
    "در صورت تغییر طبقه‌بندی HS در سال‌های دیگر، عنوان نمایشی این داشبورد همچنان عنوان مرجع ۱۳۹۶ خواهد بود."
)
