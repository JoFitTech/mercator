"""Unternehmens-Übersichtsseite."""

from __future__ import annotations

import streamlit as st
import pandas as pd
from src.services.analysis_service import AnalysisService
from src.ui.components.page_scaffold import render_page_header

def render_companies_page(service: AnalysisService) -> None:
    """Rendert die Tabellenübersicht aller Unternehmen."""
    
    # Header
    render_page_header(
        "Unternehmen", 
        "Übersicht aller getradeten Unternehmen und Profile.",
        actions=[{"label": "Refresh", "type": "secondary"}]
    )
    
    # Suche und Filter
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        search_query = c1.text_input("Suchen", placeholder="Symbol oder Name...")
        sector_options = ["Alle Sektoren"] + service.company_repo.fetch_all_sectors()
        selected_sector = c2.selectbox("Sektor", options=sector_options)
        
    # Daten laden
    df = service.get_companies(limit=1000)
    
    if df.empty:
        st.info("Keine Unternehmen in der Datenbank gefunden.")
        return

    # Filtern
    if search_query:
        mask = (
            df["symbol"].str.contains(search_query, case=False, na=False) |
            df["company_name"].str.contains(search_query, case=False, na=False)
        )
        df = df[mask]
    
    if selected_sector != "Alle Sektoren":
        df = df[df["sector"] == selected_sector]

    # Tabelle anzeigen
    if df.empty:
        st.warning("Keine Unternehmen entsprechen den Filtern.")
    else:
        # Spalten für die Anzeige vorbereiten
        display_df = df.copy()
        
        # Detail-Button-Logik via Session State
        def open_company_detail(symbol):
            st.session_state["selected_company_symbol"] = symbol
            st.rerun()

        # In Streamlit 1.35+ können wir st.dataframe mit Spalten-Konfiguration nutzen
        # Hier nutzen wir eine einfache Tabelle mit einem Selectbox/Radio oder Buttons pro Zeile
        # Da Streamlit keine Buttons in Zellen nativ gut unterstützt (außer via Data Editor oder Custom Components),
        # nutzen wir den "selected_company_symbol" State.
        
        st.markdown(f"**{len(display_df)} Unternehmen gefunden**")
        
        # Wir zeigen eine Tabelle mit einer Auswahlmöglichkeit
        selected = st.dataframe(
            display_df[[
                "symbol", "company_name", "sector", "industry", "market_cap", "last_updated_at"
            ]].rename(columns={
                "symbol": "Symbol",
                "company_name": "Unternehmen",
                "sector": "Sektor",
                "industry": "Industrie",
                "market_cap": "Market Cap",
                "last_updated_at": "Letztes Update"
            }),
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        if selected.selection.rows:
            idx = selected.selection.rows[0]
            symbol = display_df.iloc[idx]["symbol"]
            st.session_state["selected_company_symbol"] = symbol
            st.rerun()
