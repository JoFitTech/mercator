"""Streamlit-Filterkomponenten für interaktive Datenselektion."""

from __future__ import annotations

import streamlit as st


def render_ticker_filter(available_ticker: list[str]) -> str:
    """Rendert eine Ticker-Auswahl in der Sidebar und liefert den Wert zurück."""
    options = ["Alle"] + sorted(set(available_ticker))
    return st.selectbox("Ticker auswählen", options=options)
