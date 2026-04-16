"""Tabellenkomponenten für Streamlit."""

from __future__ import annotations

from typing import Any
import pandas as pd
import streamlit as st


def render_smart_table(
    df: pd.DataFrame, 
    column_config: dict | None = None, 
    height: int = 500,
    selection_mode: str = "single-row",
    on_select: str | None = None
) -> Any:
    """Rendert eine Streamlit-Tabelle mit Mercator-Standardkonfiguration."""
    if df.empty:
        st.info("Keine Daten zur Anzeige verfügbar.")
        return None

    return st.dataframe(
        df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=height,
        on_select=on_select,
        selection_mode=selection_mode,
    )
