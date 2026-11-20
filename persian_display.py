"""Presentation-only Persian number formatting for the trade dashboard.

These helpers MUST NOT alter raw data, HS keys, SQL predicates, numeric input
values or CSV downloads. They are for user-facing labels, cards and Plotly.
"""
from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd

_DIGITS = str.maketrans('0123456789٠١٢٣٤٥٦٧٨٩', '۰۱۲۳۴۵۶۷۸۹۰۱۲۳۴۵۶۷۸۹')
_NUM_TOKEN = re.compile(r'(?<![\w])[-+−]?\d[\d,.٬٫]*(?:[eE][-+]?\d+)?')
_REF = re.compile(r'%\{(x|y|customdata\[(\d+)\])(?::([^}]+))?\}')
_ANY_REF = re.compile(r'(%\{[^}]+\})')


def fa_digits(value):
    """Format any display string with Persian digits and decimal/group separators."""
    result = str(value).translate(_DIGITS)
    # Only transform punctuation BETWEEN digits, not paths, filenames or CSS.
    result = re.sub(r'(?<=[۰-۹])\.(?=[۰-۹])', '٫', result)
    result = re.sub(r'(?<=[۰-۹]),(?=[۰-۹])', '٬', result)
    return result


def fa_number(value, precision=None, grouping=True):
    """Format a NUMBER for display; preserves its underlying numeric value."""
    if value is None or pd.isna(value):
        return '—'
    try:
        v = float(value)
    except (ValueError, TypeError):
        return fa_digits(value)
    if not math.isfinite(v):
        return '—'
    if precision is not None:
        value_string = f'{v:{"," if grouping else ""}.{int(precision)}f}'
    elif v.is_integer():
        value_string = f'{int(v):,}' if grouping else str(int(v))
    else:
        decimals = 8 if 0 < abs(v) < 1e-4 else 5
        value_string = f'{v:{"," if grouping else ""}.{decimals}f}'.rstrip('0').rstrip('.')
    return fa_digits(value_string)


def _axis_samples(fig, axis):
    data = []
    for trace in fig.data:
        if trace.type not in ('scatter', 'bar', 'scattergl'):
            continue
        attr = 'x' if axis == 'xaxis' else 'y'
        axis_id = getattr(trace, 'xaxis' if attr == 'x' else 'yaxis', None) or attr
        current = attr if axis == 'xaxis' else 'y'
        if axis_id != current:
            continue  # Dashboards use the default axes; avoid interfering with subplots.
        series = getattr(trace, attr, None)
        if series is None:
            continue
        for value in series:
            if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, (bool, np.bool_)):
                if math.isfinite(float(value)):
                    data.append(float(value))
    return data


def _nice_ticks(values, *, include_zero=False, max_ticks=7):
    if not values:
        return []
    vmin, vmax = min(values), max(values)
    if include_zero:
        vmin = min(0.0, vmin)
        vmax = max(0.0, vmax)
    if vmin == vmax:
        if vmin == 0:
            return [0.0]
        vmin, vmax = (min(0., vmin), max(0., vmax))
        if vmin == vmax:
            vmin -= abs(vmin) * .1
            vmax += abs(vmax) * .1
    raw_step = (vmax - vmin) / max(1, max_ticks-1)
    base = 10 ** math.floor(math.log10(raw_step)) if raw_step else 1.0
    step = next((n*base for n in (1, 2, 2.5, 5, 10) if n*base >= raw_step), 10*base)
    start = math.floor((vmin + 1e-10*step)/step)
    end = math.ceil((vmax - 1e-10*step)/step)
    ticks = [round(k*step, 12) for k in range(start, end+1)]
    if len(ticks) < 2:
        ticks = [round(math.floor(vmin/step)*step,12), round(math.ceil(vmax/step)*step,12)]
    if len(ticks) > 10:
        ticks = ticks[::max(1, math.ceil(len(ticks)/8))]
    return list(dict.fromkeys(0.0 if abs(t)<step*1e-8 else t for t in ticks))


def _format_hover_value(value, spec=None):
    if value is None:
        return '—'
    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, (bool, np.bool_)):
        if not math.isfinite(float(value)):
            return '—'
        if spec:
            # Compatible with most Plotly D3 number formats used in this project.
            try:
                if spec.endswith('f') or spec.endswith('%') or spec.endswith('d'):
                    return fa_digits(format(float(value), spec))
                if spec.startswith(','):
                    return fa_digits(format(float(value), spec))
            except (ValueError, TypeError):
                pass
        return fa_number(value)
    return fa_digits(value)


def _convert_hover_trace(trace, x_label='x', y_label='y'):
    """Replace numeric Plotly hover substitutions with preformatted display-only data.

    Original trace x/y arrays and original customdata are left semantically
    unchanged, except for appending *string* fields exclusively used in hover.
    """
    if getattr(trace, 'hoverinfo', None) in ('skip', 'none'):
        return
    x = list(trace.x) if trace.x is not None else []
    y = list(trace.y) if trace.y is not None else []
    n = max(len(x), len(y))
    if n == 0:
        return
    raw_custom = getattr(trace, 'customdata', None)
    if raw_custom is None:
        existing = [[] for _ in range(n)]
    else:
        existing = np.asarray(raw_custom, dtype=object).tolist()
        if not isinstance(existing, list):
            existing = [[] for _ in range(n)]
        if existing and not isinstance(existing[0], (list, tuple)):
            existing = [[x] for x in existing]
        existing = [list(v) for v in existing]
        if len(existing) != n:
            return
    col_start = len(existing[0]) if existing else 0
    template = trace.hovertemplate
    if template:
        placeholders = []
        for m in _REF.finditer(template):
            full, key, ix, spec = m.group(0), m.group(1), m.group(2), m.group(3)
            if full not in [p[0] for p in placeholders]:
                placeholders.append((full, key, ix, spec))
        for j, (full, key, ix, spec) in enumerate(placeholders):
            new_idx = col_start + j
            template = template.replace(full, f'%{{customdata[{new_idx}]}}')
            for i in range(n):
                if key == 'x':
                    value = x[i] if i < len(x) else None
                elif key == 'y':
                    value = y[i] if i < len(y) else None
                else:
                    idx = int(ix)
                    value = existing[i][idx] if idx < col_start else None
                is_year = key == 'x' and str(x_label).strip() in ('سال', 'Year')
                existing[i].append(fa_number(value, grouping=False) if is_year and spec is None and isinstance(value, (int, float, np.integer, np.floating)) and float(value).is_integer() else _format_hover_value(value, spec))
        # Avoid converting digits inside Plotly substitutions (customdata indices).
        template = ''.join(
            part if part.startswith('%{') else fa_digits(part)
            for part in _ANY_REF.split(template)
        )
    else:
        # Use an explicit default hover for manually constructed Plotly traces.
        # This also avoids the implicit Plotly tooltip reintroducing Latin digits.
        for i in range(n):
            existing[i].extend([
                (fa_number(x[i], grouping=False) if str(x_label).strip() in ('سال', 'Year') and i < len(x) else _format_hover_value(x[i] if i < len(x) else None)),
                _format_hover_value(y[i] if i < len(y) else None),
            ])
        x_i, y_i = col_start, col_start+1
        parts = []
        if trace.name and not str(trace.name).startswith('trace '):
            parts.append(fa_digits(trace.name))
        parts.extend([f'{fa_digits(x_label)}: %{{customdata[{x_i}]}}',
                      f'{fa_digits(y_label)}: %{{customdata[{y_i}]}}'])
        template = '<br>'.join(parts) + '<extra></extra>'
    if existing:
        trace.customdata = existing
    trace.hovertemplate = template
    if trace.hovertext is not None:
        if isinstance(trace.hovertext, str):
            trace.hovertext = fa_digits(trace.hovertext)
        else:
            trace.hovertext = [fa_digits(x) for x in trace.hovertext]


def persianize_figure(fig):
    """Format visible chart ticks, titles, legends, and hover with Persian digits.

    Called at final render time: all numeric data and filtering stay numeric.
    """
    # The Plotly 'x unified' heading uses unformatted raw x values; keep
    # multi-series hover but avoid that extra Latin-numeral heading.
    if fig.layout.hovermode == 'x unified':
        fig.update_layout(hovermode='x')
    elif fig.layout.hovermode == 'y unified':
        fig.update_layout(hovermode='y')
    x_axis, y_axis = fig.layout.xaxis, fig.layout.yaxis
    x_label = x_axis.title.text if x_axis.title and x_axis.title.text else 'سال / گروه'
    y_label = y_axis.title.text if y_axis.title and y_axis.title.text else 'مقدار'

    for axis_name in ('xaxis', 'yaxis'):
        axis = getattr(fig.layout, axis_name)
        if axis.ticktext:
            axis.ticktext = [fa_digits(t) for t in axis.ticktext]
        elif axis.tickmode != 'array' and axis.type not in ('category', 'date', 'log', 'multicategory'):
            vals = _axis_samples(fig, axis_name)
            is_bar = any(t.type == 'bar' for t in fig.data)
            ticks = _nice_ticks(vals, include_zero=is_bar)
            if ticks:
                axis.tickmode = 'array'
                axis.tickvals = ticks
                axis.ticktext = [fa_number(t) for t in ticks]
        if axis.title and axis.title.text:
            axis.title.text = fa_digits(axis.title.text)
    if fig.layout.title and fig.layout.title.text:
        fig.layout.title.text = fa_digits(fig.layout.title.text)
    for trace in fig.data:
        if trace.name:
            trace.name = fa_digits(trace.name)
        if trace.text is not None:
            if isinstance(trace.text, str):
                trace.text = fa_digits(trace.text)
            else:
                trace.text = [fa_digits(v) for v in trace.text]
        _convert_hover_trace(trace, x_label=x_label, y_label=y_label)
    return fig


def persian_dataframe(df):
    """Display a Persian-digit copy; keep original numeric df for CSV exports."""
    show = df.copy()
    for col in show.columns:
        if pd.api.types.is_numeric_dtype(show[col]):
            if str(col).strip() in ('سال', 'Year'):
                show[col] = show[col].map(lambda x: fa_number(x, precision=0, grouping=False))
            else:
                precision = 0 if pd.api.types.is_integer_dtype(show[col]) else 2
                show[col] = show[col].map(lambda x: fa_number(x, precision=precision))
        else:
            show[col] = show[col].map(lambda x: fa_digits(x) if pd.notna(x) else '—')
    return show
