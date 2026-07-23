"""Shared Streamlit table configuration with centered cell content."""

from __future__ import annotations

from html import escape
from numbers import Real

import pandas as pd
import streamlit as st


def centered_text(label=None, **kwargs):
    return st.column_config.TextColumn(label, alignment="center", **kwargs)


def centered_number(label=None, **kwargs):
    return st.column_config.NumberColumn(label, alignment="center", **kwargs)


def centered_columns(data) -> dict:
    """Build centered configs for every visible column in a read-only table."""
    frame = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    config = {}
    for name in frame.columns:
        if pd.api.types.is_numeric_dtype(frame[name].dtype):
            config[name] = centered_number(str(name))
        else:
            config[name] = centered_text(str(name))
    return config


def centered_dataframe(data, **kwargs):
    """Render a scrollable read-only HTML table with truly centered headers."""
    # Do not leak Streamlit's DeltaGenerator return value to callers.  A bare
    # wrapper call can otherwise be picked up by Streamlit's magic display and
    # rendered as the internal DeltaGenerator help page.
    st.markdown(centered_table_html(data, **kwargs), unsafe_allow_html=True)


def _cell_text(value) -> str:
    if value is None:
        return "None"
    try:
        if bool(pd.isna(value)):
            return "None"
    except (TypeError, ValueError):
        pass
    if isinstance(value, Real) and not isinstance(value, bool):
        return f"{float(value):.4f}".rstrip("0").rstrip(".")
    return str(value)


def centered_table_html(data, max_height="32rem") -> str:
    """Build escaped table markup because Streamlit's canvas headers ignore CSS."""
    frame = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    headers = "".join(f"<th>{escape(str(name))}</th>" for name in frame.columns)
    rows = []
    for values in frame.itertuples(index=False, name=None):
        cells = "".join(f"<td>{escape(_cell_text(value))}</td>" for value in values)
        rows.append(f"<tr>{cells}</tr>")
    return f"""
    <style>
    .drc-centered-table-wrap {{
        max-height: {escape(str(max_height))};
        overflow: auto;
        border-radius: 0.5rem;
    }}
    .drc-centered-table {{
        width: 100%;
        min-width: max-content;
        border-collapse: collapse;
        color: var(--text-color);
        font-size: 0.9rem;
    }}
    .drc-centered-table th,
    .drc-centered-table td {{
        height: 3.5rem;
        padding: 0 0.75rem;
        border: 1px solid rgba(128, 128, 128, 0.28);
        text-align: center !important;
        vertical-align: middle !important;
        line-height: 1.25rem;
        white-space: nowrap;
    }}
    .drc-centered-table th {{
        position: sticky;
        top: 0;
        z-index: 1;
        background: var(--secondary-background-color);
        font-weight: 600;
    }}
    </style>
    <div class="drc-centered-table-wrap">
      <table class="drc-centered-table">
        <thead><tr>{headers}</tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """
