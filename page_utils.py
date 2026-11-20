
import html
import math
import re
import textwrap

import numpy as np
import pandas as pd

from persian_display import fa_digits, fa_number

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

# Marker for verifying the patch in local VS Code / GitHub.
METRIC_CARD_RENDERER = "compact-v5-persian-digits"


def _split_metric_value(value):
    """Keep the numeric part and unit separate, with a compact percentage case."""
    raw = "—" if value is None else str(value).strip()
    if not raw:
        return "—", "", False
    match = re.fullmatch(r"([+\-−]?[0-9۰-۹٠-٩][0-9۰-۹٠-٩,.٫٬]*)\s*([٪%])", raw)
    if match:
        return match.group(1), match.group(2), True
    match = re.match(r"^([+\-−]?[0-9۰-۹٠-٩][0-9۰-۹٠-٩,.٫٬]*)\s*(.*)$", raw)
    if match:
        return match.group(1), match.group(2).strip(), False
    return raw, "", False


def metric_card(container, label, value, delta=None):
    """Compact responsive KPI matching the original design, without Markdown.

    The previous native Streamlit version fixed leaked closing tags but used an
    H3 heading, so both numeric values and units inherited oversized heading
    typography.  This version renders *one HTML fragment* through st.html,
    entirely bypassing the Markdown parser that caused literal ``</div>``.
    All user-facing strings are HTML-escaped, and small inline styles isolate
    the card from changes in Streamlit's theme or global CSS selectors.
    """
    safe_label = html.escape("" if label is None else fa_digits(label), quote=True)
    number, unit, is_percentage = _split_metric_value(value)
    raw_value = "—" if value is None else fa_digits(value)
    safe_number = html.escape(fa_digits(number))
    safe_unit = html.escape(fa_digits(unit))

    # Five-column layouts have only ~180px per card. Scale very long numbers a bit.
    number_size = "1.28rem" if len(number) > 8 else "1.52rem"

    if is_percentage:
        # The number and percentage sign stay in one LTR bidi-isolated group.
        formatted_value = (
            f'<bdi dir="ltr" style="font-size:{number_size};font-weight:800;'
            f'line-height:1.35;white-space:nowrap;color:#172033;'
            f'font-variant-numeric:tabular-nums">{safe_number}{safe_unit}</bdi>'
        )
    else:
        formatted_value = (
            f'<bdi dir="ltr" style="font-size:{number_size};font-weight:800;'
            f'line-height:1.35;white-space:nowrap;color:#172033;'
            f'font-variant-numeric:tabular-nums">{safe_number}</bdi>'
        )
        if unit:
            formatted_value += (
                f'<small dir="rtl" style="font-size:0.79rem;line-height:1.55;'
                f'font-weight:500;color:#334155;white-space:normal;'
                f'overflow-wrap:normal">{safe_unit}</small>'
            )

    delta_html = ""
    if delta is not None and str(delta).strip() not in ("", "—", "nan", "None"):
        raw_delta = fa_digits(str(delta).strip())
        negative = raw_delta.startswith(("-", "−"))
        fg, bg = ("#b42318", "#fff1f0") if negative else ("#176b50", "#eef9f3")
        arrow = "↓" if negative else "↑"
        # Delta may contain Persian units; keep the text itself RTL, numeric
        # runs stay visually stable under the outer bidi isolation.
        delta_html = (
            f'<div dir="rtl" style="margin-top:auto;align-self:flex-start;'
            f'display:inline-flex;align-items:center;gap:4px;max-width:100%;'
            f'background:{bg};color:{fg};border-radius:99px;padding:3px 8px;'
            f'font-size:0.74rem;font-weight:600;line-height:1.4;'
            f'white-space:normal"><span aria-hidden="true">{arrow}</span>'
            f'<bdi dir="auto">{html.escape(raw_delta)}</bdi></div>'
        )

    content = (
        f'<div class="trade-kpi-compact" dir="rtl" role="group" '
        f'aria-label="{safe_label}: {html.escape(raw_value, quote=True)}" '
        f'style="box-sizing:border-box;width:100%;min-height:132px;'
        f'padding:14px 14px 13px;border:1px solid #e7ebef;'
        f'border-radius:17px;background:#fff;'
        f'box-shadow:0 2px 8px rgba(15,23,42,.025);'
        f'display:flex;flex-direction:column;align-items:flex-start;'
        f'justify-content:flex-start;gap:8px;direction:rtl;text-align:right;'
        f'font-family:Vazirmatn,Tahoma,Arial,sans-serif">'
        f'<div style="font-size:0.89rem;font-weight:600;line-height:1.65;'
        f'color:#172033;overflow-wrap:break-word">{safe_label}</div>'
        f'<div dir="rtl" style="display:flex;flex-wrap:wrap;'
        f'align-items:baseline;justify-content:flex-start;column-gap:5px;'
        f'row-gap:0;min-width:0;width:100%;direction:rtl;'
        f'text-align:right">{formatted_value}</div>'
        f'{delta_html}</div>'
    )
    # st.html / container.html renders one complete fragment directly, not via
    # Markdown; this prevents a closing tag from becoming a visible code block.
    container.html(content)


def _axis_label(label, *, long=False):
    """Fit SVG axis labels into a reserved column while preserving hover text."""
    label = " ".join(str(label).split())
    if not label:
        return ""
    if not long:
        # Right-to-left marker prevents country/custom names being mirrored.
        return "\u200f" + html.escape(fa_digits(label))

    # A readable two-line abbreviation is necessary for long HS descriptions.
    # The underlying category remains intact and Plotly hover retains full text.
    parts = textwrap.wrap(label, width=34, break_long_words=False,
                          break_on_hyphens=False)
    if len(parts) > 2:
        parts = parts[:2]
        parts[1] = parts[1].rstrip(" ،؛—-") + "…"
    return "<br>".join("\u200f" + html.escape(fa_digits(x)) for x in parts)


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
        ticktext=[fa_digits(str(y)) for y in ticks],
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
        return fa_digits(f"{value / 1e9:,.2f} میلیارد دلار")
    if metric == "وزن":
        return fa_digits(f"{value / 1e9:,.2f} میلیون تن")
    return fa_digits(f"{value:,.0f} دلار/تن")
