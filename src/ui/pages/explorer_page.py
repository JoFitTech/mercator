"""Explorer-Seite mit interaktiven Filtern auf bereinigte Trades."""

from __future__ import annotations

import streamlit as st

from src.services.analysis_service import AnalysisService


def render_explorer_page(service: AnalysisService) -> None:
    """Rendert Filter und Tabelle für bereinigte MySQL-Daten."""
    st.title("Explorer")
    st.caption("Interaktive Filter- und Tabellenansicht für bereinigte Finanzdaten.")

    symbol = st.text_input("Symbol")
    transaction_type = st.text_input("transaction_type")
    gate_status = st.selectbox("gate_status", ["", "PASS", "PENDING", "FAIL"])
    sector = st.text_input("sector")
    country = st.text_input("country")

    filters = {
        "symbol": symbol.strip().upper() or None,
        "transaction_type": transaction_type.strip() or None,
        "gate_status": gate_status or None,
        "sector": sector.strip() or None,
        "country": country.strip() or None,
    }

    data = service.get_filtered_trades(filters=filters, limit=500)
    if data.empty:
        st.info("Keine Daten für die aktuelle Filterkombination gefunden.")
        return

    st.dataframe(data, use_container_width=True)
    st.download_button(
        label="Export als CSV",
        data=data.to_csv(index=False).encode("utf-8"),
        file_name="explorer_export.csv",
        mime="text/csv",
    )
