"""Detailseite für tickerbezogene Auswertungen."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.components.tables import render_dataframe_table


def render_ticker_detail_page(trades_df: pd.DataFrame) -> None:
    """Rendert Detaildaten und Platzhalter für spätere Bewertungslogik."""
    st.title("Ticker-Detailansicht")
    st.caption(
        "Detaillierte Sicht auf ausgewählte Unternehmen, Transaktionen und vorbereitete Analysekennzahlen."
    )

    if trades_df.empty or "ticker" not in trades_df.columns:
        st.info("Für die Detailansicht sind derzeit noch keine geeigneten Daten verfügbar.")
        return

    ticker = st.selectbox("Ticker wählen", options=sorted(trades_df["ticker"].dropna().unique()))
    detail_df = trades_df[trades_df["ticker"] == ticker]

    st.subheader(f"Kennzahlen für {ticker}")
    st.metric("Anzahl Transaktionen", int(len(detail_df.index)))
    st.caption("TODO: Score-/Gate-Logik nach finaler Fachdefinition ergänzen.")

    st.subheader("Historie / Event-Liste")
    render_dataframe_table(detail_df)
