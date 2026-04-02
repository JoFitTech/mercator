"""Ticker-Detailseite mit Profil, Trades und Kennzahlen."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.services.analysis_service import AnalysisService


def render_ticker_detail_page(service: AnalysisService) -> None:
    """Rendert die Detailansicht für ein ausgewähltes Symbol."""
    st.title("Ticker-Detailansicht")
    st.caption(
        "Detaillierte Sicht auf ausgewählte Unternehmen, Transaktionen und vorbereitete Analysekennzahlen."
    )

    all_rows = service.get_filtered_trades(limit=200)
    if all_rows.empty or "symbol" not in all_rows.columns:
        st.info("Für die Detailansicht sind aktuell keine Daten verfügbar.")
        return

    symbols = sorted(s for s in all_rows["symbol"].dropna().unique().tolist() if s)
    selected = st.selectbox("Symbol", symbols)

    result = service.get_ticker_detail(selected)

    st.subheader("Firmenprofil")
    if result.company_profile:
        st.json(result.company_profile)
    else:
        st.info("Für dieses Symbol ist aktuell kein Firmenprofil verfügbar.")

    st.subheader("Einfache Kennzahlen")
    c1, c2, c3 = st.columns(3)
    c1.metric("Trades", result.metrics.get("trade_count", 0))
    c2.metric("Ø Preis", f"{result.metrics.get('avg_price', 0):.2f}")
    c3.metric("Gesamtmenge", f"{result.metrics.get('total_qty', 0):.0f}")

    st.subheader("Vorbereitete Analyse-Sektion")
    st.info(result.note)

    st.subheader("Letzte Insider-Trades")
    st.dataframe(pd.DataFrame(result.rows), use_container_width=True)
