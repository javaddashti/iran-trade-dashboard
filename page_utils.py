
import html
import math
import re
import textwrap

import numpy as np
import pandas as pd

_RLI = "\u2067"
_PDI = "\u2069"

def rtl_text(value):
    if value is None or pd.isna(value):
        return ""
    return f"{_RLI}{value}{_PDI}"

def unit_value(df):
    out = df.copy()
    out["Dollar_Value"] = pd.to_numeric(out["Dollar_Value"], errors="coerce")
    out["Weight_kg"] = pd.to_numeric(out["Weight_kg"], errors="coerce")

    valid = out["Weight_kg"].gt(0)
    out["Unit_Value"] = np.nan
    out.loc[valid, "Unit_Value"] = (
        out.loc[valid, "Dollar_Value"]
        / (out.loc[valid, "Weight_kg"] / 1000.0)
    )

    numeric = pd.to_numeric(out["Unit_Value"], errors="coerce").to_numpy(dtype=float)
    out.loc[~np.isfinite(numeric), "Unit_Value"] = np.nan
    return out

def metric_column(metric):
    return {
        "ارزش دلاری": "Dollar_Value",
        "وزن": "Weight_kg",
        "ارزش هر تن": "Unit_Value",
    }[metric]

def metric_scaled(series, metric):
    """Choose readable chart units without tiny SI ticks such as 20µ billion.

    The underlying values stay unchanged, only the chart scale/title varies.
    """
    valid = pd.to_numeric(pd.Series(series), errors="coerce")
    magnitude = valid.abs().max()
    magnitude = 0 if pd.isna(magnitude) else float(magnitude)
    if metric == "ارزش دلاری":
        if magnitude >= 1e9:
            return series / 1e9, "میلیارد دلار"
        if magnitude >= 1e6:
            return series / 1e6, "میلیون دلار"
        if magnitude >= 1e3:
            return series / 1e3, "هزار دلار"
        return series, "دلار"
    if metric == "وزن":
        if magnitude >= 1e9:
            return series / 1e9, "میلیون تن"
        if magnitude >= 1e6:
            return series / 1e6, "هزار تن"
        if magnitude >= 1e3:
            return series / 1e3, "تن"
        return series, "کیلوگرم"
    return series, "دلار به ازای هر تن"

# This marker helps verify that the intended file is installed locally and on GitHub.
METRIC_CARD_RENDERER = "native-v3-no-html"


def metric_card(container, label, value, delta=None):
    """Render a KPI as native Streamlit widgets, not embedded HTML.

    The older HTML implementation sometimes leaked a literal </div> into
    Markdown output for cards without a delta. This implementation contains
    no HTML tags at all, so that failure mode is impossible. It preserves
    all label/value/delta strings and uses a bordered native container.
    """
    raw_label = str(label) if label is not None else ""
    raw_value = str(value) if value is not None else "—"

    # st.columns objects are DeltaGenerators and support .container().
    card = container.container(border=True)
    card.markdown(f"**{raw_label}**")
    card.markdown(f"### {raw_value}")

    if delta is not None:
        raw_delta = str(delta).strip()
        if raw_delta not in ("", "—", "nan", "None"):
            downward = raw_delta.startswith(("-", "−"))
            color = "red" if downward else "green"
            arrow = "↓" if downward else "↑"
            card.markdown(f":{color}[{arrow} {raw_delta}]")


def _axis_label(label, *, long=False):
    """Fit SVG axis labels into a reserved column while preserving hover text."""
    label = " ".join(str(label).split())
    if not label:
        return ""
    if not long:
        # Right-to-left marker prevents country/custom names being mirrored.
        return "\u200f" + html.escape(label)

    # A readable two-line abbreviation is necessary for long HS descriptions.
    # The underlying category remains intact and Plotly hover retains full text.
    parts = textwrap.wrap(label, width=34, break_long_words=False,
                          break_on_hyphens=False)
    if len(parts) > 2:
        parts = parts[:2]
        parts[1] = parts[1].rstrip(" ،؛—-") + "…"
    return "<br>".join("\u200f" + html.escape(x) for x in parts)


def horizontal_bar_layout(fig, categories, *, long=False):
    """Make horizontal-bar Persian category labels legible (not clipped)."""
    labels = [str(x) for x in categories]
    max_label_length = max((len(x) for x in labels), default=0)
    # Customs names can be far longer than country names; reserve enough space.
    left_margin = 310 if long else max(215, min(340, math.ceil(max_label_length * 6.8) + 30))
    fig.update_layout(
        margin=dict(l=left_margin, r=28, t=80, b=50),
        hoverlabel=dict(align="right"),
    )
    fig.update_yaxes(
        tickmode="array",
        tickvals=labels,
        ticktext=[_axis_label(x, long=long) for x in labels],
        automargin=True,
        tickfont=dict(size=12, family="Vazirmatn, Tahoma, Arial, sans-serif"),
        ticklabelposition="outside",
        title_text="",
    )
    return fig


def fix_year_axis(fig, years):
    """Display integer Iranian calendar years only, never e.g. 1401.5."""
    valid = pd.to_numeric(pd.Series(list(years)), errors="coerce").dropna()
    if valid.empty:
        return fig
    unique_years = sorted(set(int(y) for y in valid if math.isfinite(float(y))))
    if not unique_years:
        return fig
    step = max(1, math.ceil(len(unique_years) / 16))
    ticks = unique_years[::step]
    if unique_years[-1] not in ticks:
        ticks.append(unique_years[-1])
    fig.update_xaxes(
        type="linear",
        tickmode="array",
        tickvals=ticks,
        ticktext=[str(y) for y in ticks],
        tickangle=0,
        automargin=True,
        title_text="سال",
    )
    return fig


def chart_layout(fig, height=430, y_title=None, hovermode="x unified"):
    """Consistent chart style for Persian RTL pages."""
    fig.update_layout(
        height=height,
        margin=dict(l=70, r=35, t=82, b=48),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Vazirmatn, Tahoma, Arial, sans-serif", size=13),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.03,
            xanchor="left", x=0,
            font=dict(family="Vazirmatn, Tahoma, Arial, sans-serif"),
        ),
        hoverlabel=dict(align="right"),
        hovermode=hovermode,
    )
    title_text = fig.layout.title.text
    if title_text:
        fig.update_layout(title=dict(
            text="\u200f" + str(title_text), x=1, xanchor="right",
            font=dict(family="Vazirmatn, Tahoma, Arial, sans-serif", size=17),
        ))
    fig.update_xaxes(
        showgrid=False, automargin=True,
        tickfont=dict(family="Vazirmatn, Tahoma, Arial, sans-serif"),
        title_font=dict(family="Vazirmatn, Tahoma, Arial, sans-serif"),
    )
    fig.update_yaxes(
        automargin=True, gridcolor="rgba(15,23,42,0.08)",
        zeroline=True, zerolinecolor="rgba(15,23,42,0.24)",
        title=y_title,
        tickfont=dict(family="Vazirmatn, Tahoma, Arial, sans-serif"),
        title_font=dict(family="Vazirmatn, Tahoma, Arial, sans-serif"),
    )
    return fig


def top_share_cards(df, value_col="Dollar_Value", ns=(3, 5, 10)):
    total = pd.to_numeric(df[value_col], errors="coerce").sum()
    if not total or pd.isna(total):
        return [None for _ in ns]
    return [
        100 * pd.to_numeric(
            df.nlargest(n, value_col)[value_col], errors="coerce"
        ).sum() / total
        for n in ns
    ]

def hhi_from_values(values):
    s = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    total = s.sum()
    if total <= 0:
        return None
    shares = 100 * s / total
    return float((shares ** 2).sum())

def yoy_from_table(df, year, value_col="Dollar_Value"):
    cur = pd.to_numeric(
        df.loc[df["Year"].eq(year), value_col], errors="coerce"
    ).sum()
    prev = pd.to_numeric(
        df.loc[df["Year"].eq(year - 1), value_col], errors="coerce"
    ).sum()
    if prev == 0 or pd.isna(prev):
        return None
    return (cur / prev - 1) * 100

def format_number(value, metric):
    if value is None or pd.isna(value):
        return "—"
    if metric == "ارزش دلاری":
        return f"{value / 1e9:,.2f} میلیارد دلار"
    if metric == "وزن":
        return f"{value / 1e9:,.2f} میلیون تن"
    return f"{value:,.0f} دلار/تن"
