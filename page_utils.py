
import numpy as np
import pandas as pd

_RLI = "\u2067"
_PDI = "\u2069"

def rtl_text(value):
    """Wrap Persian/mixed labels so Plotly handles RTL text more reliably."""
    if value is None or pd.isna(value):
        return ""
    return f"{_RLI}{value}{_PDI}"

def prepare_hs_labels(df):
    x = df.copy()
    x["HS2"] = x["HS2"].astype("string").str.zfill(2)

    if "HS2_desc" in x.columns:
        desc = x["HS2_desc"].fillna("بدون عنوان").astype(str)
        x["Label"] = x["HS2"].astype(str) + " — " + desc
    else:
        x["Label"] = "HS " + x["HS2"].astype(str)

    return x

def unit_value(df):
    """
    Calculate dollars per ton safely.
    Fixes the former pd.isfinite error (pandas has no isfinite attribute).
    """
    out = df.copy()

    out["Dollar_Value"] = pd.to_numeric(out["Dollar_Value"], errors="coerce")
    out["Weight_kg"] = pd.to_numeric(out["Weight_kg"], errors="coerce")

    valid_weight = out["Weight_kg"].gt(0)

    out["Unit_Value"] = np.nan
    out.loc[valid_weight, "Unit_Value"] = (
        out.loc[valid_weight, "Dollar_Value"]
        / (out.loc[valid_weight, "Weight_kg"] / 1000.0)
    )

    finite_mask = np.isfinite(
        pd.to_numeric(out["Unit_Value"], errors="coerce").to_numpy(dtype=float)
    )
    out.loc[~finite_mask, "Unit_Value"] = np.nan

    return out

def metric_column(metric):
    return {
        "ارزش دلاری": "Dollar_Value",
        "وزن": "Weight_kg",
        "ارزش هر تن": "Unit_Value",
    }[metric]

def metric_scaled(series, metric):
    if metric == "ارزش دلاری":
        return series / 1e9, "میلیارد دلار"
    if metric == "وزن":
        return series / 1e9, "میلیون تن"
    return series, "دلار به ازای هر تن"

def chart_layout(fig, height=430, y_title=None, hovermode="x unified"):
    fig.update_layout(
        height=height,
        margin=dict(l=24, r=28, t=66, b=28),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(
            family="Vazirmatn, Tahoma, Arial, sans-serif",
            size=13,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(family="Vazirmatn, Tahoma, Arial, sans-serif"),
        ),
        hovermode=hovermode,
    )

    # Right-align chart titles if a title already exists.
    title_text = fig.layout.title.text
    if title_text:
        fig.update_layout(
            title=dict(
                text=rtl_text(title_text),
                x=1,
                xanchor="right",
                y=0.98,
                yanchor="top",
                font=dict(
                    family="Vazirmatn, Tahoma, Arial, sans-serif",
                    size=18,
                ),
            )
        )

    fig.update_xaxes(
        showgrid=False,
        tickfont=dict(family="Vazirmatn, Tahoma, Arial, sans-serif"),
        title_font=dict(family="Vazirmatn, Tahoma, Arial, sans-serif"),
    )

    fig.update_yaxes(
        gridcolor="rgba(15,23,42,0.08)",
        zeroline=True,
        zerolinecolor="rgba(15,23,42,0.24)",
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
        100
        * pd.to_numeric(df.nlargest(n, value_col)[value_col], errors="coerce").sum()
        / total
        for n in ns
    ]

def hhi_from_values(values):
    s = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    total = s.sum()

    if total <= 0:
        return None

    shares_pct = 100 * s / total
    return float((shares_pct ** 2).sum())

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
