"""Chart-Helfer für die Streamlit-Oberfläche."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_bar_chart(df: pd.DataFrame, x: str, y: str) -> None:
    """Zeigt ein einfaches Balkendiagramm, falls Daten vorhanden sind."""
    if df.empty or x not in df.columns or y not in df.columns:
        st.info("Für das Diagramm sind aktuell keine geeigneten Daten vorhanden.")
        return

    st.bar_chart(df.set_index(x)[y])
