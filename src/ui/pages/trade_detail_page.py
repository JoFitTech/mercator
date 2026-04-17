"""Trade-Detail-Unterseite."""

from __future__ import annotations

import streamlit as st
import pandas as pd
from src.services.analysis_service import AnalysisService
from src.ui.components.page_scaffold import render_page_header, render_error_state
from src.ui.components.status_badges import score_class_badge, status_badge

def render_trade_detail_page(service: AnalysisService, dedupe_key: str) -> None:
    """Rendert die Detailansicht für einen einzelnen Trade."""
    
    # Trade laden
    df = service.trade_repo.fetch_trades(filters={"dedupe_key": dedupe_key}, limit=1)
    if df.empty:
        render_error_state(f"Trade mit Key {dedupe_key} nicht gefunden.")
        if st.button("Zurück zu Trades"):
            st.session_state["selected_trade_key"] = None
            st.rerun()
        return

    trade = df.iloc[0]
    symbol = trade.get("symbol_at_trade", "N/A")
    insider = trade.get("reporting_name", "N/A")

    # Header
    col_title, col_actions = st.columns([0.7, 0.3], vertical_alignment="center")
    with col_title:
        render_page_header(f"Trade Detail: {symbol}", f"Insider: {insider}")
    
    with col_actions:
        if st.button("← Zurück zur Liste", use_container_width=True):
            st.session_state["selected_trade_key"] = None
            st.rerun()

    # 1. Summary
    st.subheader("Trade Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Datum", trade.get("transaction_date", "N/A"))
    c2.metric("Richtung", trade.get("direction") or trade.get("acquisition_or_disposition", "N/A"))
    c3.metric("Wert est.", f"${trade.get('trade_value_estimated', 0):,.2f}")
    c4.metric("Menge", f"{trade.get('qty', 0):,.0f}")

    # 2. Status & Scoring
    st.markdown("---")
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("Validation & Gate")
        v1, v2 = st.columns(2)
        with v1:
            st.write("**Validation Status**")
            status_badge(trade.get("validation_status", "UNCHECKED"))
        with v2:
            st.write("**Gate Status**")
            status_badge(trade.get("gate_status", "PENDING"))
        
        if trade.get("gate_reason"):
            st.info(f"**Gate Grund:** {trade.get('gate_reason')}")

    with col_right:
        st.subheader("Scoring")
        s1, s2 = st.columns(2)
        with s1:
            st.write("**Score Klasse**")
            score_class_badge(trade.get("score_class", "F"))
        with s2:
            st.write("**Score Wert**")
            st.metric("Score", f"{trade.get('score', 0):.2f}")

    # 3. Technische Metadaten & Links
    st.markdown("---")
    st.subheader("Technische Details & Quellen")
    t1, t2 = st.columns(2)
    with t1:
        st.write(f"**Form Type:** {trade.get('form_type', 'N/A')}")
        st.write(f"**Security:** {trade.get('security_name', 'N/A')}")
        st.write(f"**Owner Type:** {trade.get('type_of_owner', 'N/A')}")
    
    with t2:
        st.write(f"**Filing Date:** {trade.get('filing_date', 'N/A')}")
        st.write(f"**Dedupe Key:** `{trade.get('dedupe_key', 'N/A')}`")
        if trade.get("source_url"):
            st.link_button("SEC Filing / Source", trade.get("source_url"), use_container_width=True)

    # 4. Unternehmenskontext
    st.markdown("---")
    st.subheader("Unternehmen")
    if st.button(f"Deep-Dive: {symbol}", use_container_width=True):
        st.session_state["selected_company_symbol"] = symbol
        st.session_state["selected_trade_key"] = None # Optional: Trade-Key löschen, wenn wir zum Unternehmen springen
        st.rerun()
