"""Tabellenkomponenten für Streamlit."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_dataframe_table(df: pd.DataFrame, max_rows: int = 200) -> None:
    """Zeigt eine DataFrame-Vorschau mit Zeilenlimit an."""
    if df.empty:
        st.info("Es liegen derzeit keine Datensätze zur Anzeige vor.")
        return
    st.dataframe(df.head(max_rows), use_container_width=True)
