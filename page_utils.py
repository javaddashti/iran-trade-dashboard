
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
    if metric == "ارزش دلاری":
        return series / 1e9, "میلیارد دلار"
    if metric == "وزن":
        return series / 1e9, "میلیون تن"
    return series, "دلار به ازای هر تن"

def chart_layout(fig, height=430, y_title=None, hovermode="x unified"):
    fig.update_layout(
        height=height,
        margin=dict(l=42, r=38, t=66, b=38),
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

    title_text = fig.layout.title.text
    if title_text:
        fig.update_layout(
            title=dict(
                text=rtl_text(title_text),
                x=1,
                xanchor="right",
                font=dict(
                    family="Vazirmatn, Tahoma, Arial, sans-serif",
                    size=18,
                ),
            )
        )

    fig.update_xaxes(
        showgrid=False,
        automargin=True,
        tickfont=dict(family="Vazirmatn, Tahoma, Arial, sans-serif"),
        title_font=dict(family="Vazirmatn, Tahoma, Arial, sans-serif"),
    )
    fig.update_yaxes(
        automargin=True,
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
