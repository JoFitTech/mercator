"""Trade-Detailseite (Requirement 5)."""

from __future__ import annotations
import streamlit as st
import pandas as pd
from src.services.analysis_service import AnalysisService
from src.services.database_status_service import DatabaseStatus
from src.ui.components.page_scaffold import render_page_header, render_empty_state, render_kpi_row
from src.ui.components.status_badges import score_class_badge, status_badge

def render_trade_detail_page(service: AnalysisService | None, dedupe_key: str | None = None, db_status: DatabaseStatus | None = None) -> None:
    """Rendert die Detailseite für einen einzelnen Trade."""
    if service is None:
        render_empty_state("Trade-Details sind derzeit nicht verfügbar, da die Analyse-Datenbank offline ist.")
        return
    if not dedupe_key:
        dedupe_key = st.session_state.get("selected_trade_key")
        
    if not dedupe_key:
        render_empty_state("Kein Trade ausgewählt.")
        if st.button("Zurück zur Trades-Übersicht"):
            st.session_state["nav_target"] = "Trades"
            st.rerun()
        return

    # Daten laden
    with st.spinner("Lade Trade-Details..."):
        # Wir nutzen fetch_trades mit dedupe_key Filter
        try:
            trades = service.trade_repo.fetch_trades(filters={"dedupe_key": dedupe_key}, limit=1)
        except Exception as e:
            st.error(f"Fehler beim Laden des Trades: {e}")
            return
        
    if trades.empty:
        render_empty_state(f"Trade mit Key '{dedupe_key}' nicht gefunden.")
        if st.button("Zurück zur Trades-Übersicht"):
            st.session_state["nav_target"] = "Trades"
            st.rerun()
        return

    trade = trades.iloc[0]
    
    # Header (Requirement 5.2)
    render_page_header(
        f"{trade.get('symbol_at_trade')} - {trade.get('reporting_name')}",
        f"{trade.get('acquisition_or_disposition')} am {trade.get('transaction_date')}"
    )

    # 1. KPI-Übersicht (Requirement 5.2)
    kpis = [
        {"label": "Wert", "value": f"${trade.get('trade_value_estimated', 0):,.0f}"},
        {"label": "Score", "value": str(trade.get("score", 0))},
        {"label": "Klasse", "value": str(trade.get("score_class", "E"))},
    ]
    render_kpi_row(kpis)

    # 2. Sektionen (Requirement 5.2)
    c1, c2 = st.columns(2)
    
    with c1:
        with st.container(border=True):
            st.subheader("Trade-Informationen")
            st.write(f"**Symbol:** {trade.get('symbol_at_trade')}")
            st.write(f"**Insider:** {trade.get('reporting_name')}")
            st.write(f"**Rolle:** {trade.get('type_of_owner')}")
            st.write(f"**Richtung:** {trade.get('acquisition_or_disposition')}")
            st.write(f"**Menge:** {trade.get('qty', 0):,.0f}")
            st.write(f"**Preis:** ${trade.get('price', 0):,.2f}")
            st.write(f"**Datum:** {trade.get('transaction_date')}")
            st.write(f"**Filing:** {trade.get('filing_date')}")

    with c2:
        with st.container(border=True):
            st.subheader("Status & Scoring")
            st.write("**Gate Status:**", trade.get("gate_status"))
            st.write("**Gate Reason:**", trade.get("gate_reason") or "N/A")
            st.write("**Validation:**", trade.get("validation_status"))
            st.write("**Dashboard Valid:**", "Ja" if trade.get("dashboard_valid") else "Nein")
            st.write("**Dedupe Key:**", f"`{trade.get('dedupe_key')}`")
            if trade.get("source_url"):
                st.link_button("Original SEC Filing öffnen", trade.get("source_url"))

    # 3. Insider Quality (Requirement 4.4)
    st.markdown("---")
    st.subheader("Insider-Qualität")
    quality = service.compute_insider_quality(trade.get("reporting_name"))
    if quality:
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Qualitäts-Score", f"{quality['quality_score']:.1f}")
        q2.metric("Historische Trades", quality["trade_count"])
        q3.metric("Gate PASS Rate", f"{quality['gate_pass_share']}%")
        q4.metric("Kauf-Anteil", f"{quality['buy_share']}%")
    else:
        st.info("Keine ausreichende Historie für Qualitäts-Metriken.")

    # Zurück Button
    if st.button("Zurück zur Übersicht", use_container_width=True):
        st.session_state["nav_target"] = "Trades"
        st.rerun()
