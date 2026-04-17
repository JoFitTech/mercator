"""Ticker-Detailseite mit Profil, Trades und Kennzahlen."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.services.analysis_service import AnalysisService
from src.ui.components.context_bar import render_context_bar
from src.ui.components.page_scaffold import render_empty_state, render_kpi_row, render_page_header
from src.ui.components.status_badges import status_badge
from src.ui.components.tables import render_trade_table


def format_mcap(value: Any, currency: str = "USD") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value == 0:
        return "Keine Daten verfügbar"
    try:
        return f"{float(value):,.0f} {currency}"
    except (ValueError, TypeError):
        return "Keine Daten verfügbar"


def format_number(value: Any, format_spec: str = "{:,.2f}", na_rep: str = "-") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return na_rep
    try:
        return format_spec.format(float(value))
    except (ValueError, TypeError):
        return na_rep


def _safe_select_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    safe_df = frame.copy()
    for col in columns:
        if col not in safe_df.columns:
            safe_df[col] = pd.NA
    return safe_df[columns]


def render_company_detail_page(service: AnalysisService, symbol: str | None = None) -> None:
    """Rendert den Company Intelligence Workspace."""
    
    # 1. Symbol bestimmen
    current_ticker = symbol or st.session_state.get("selected_company_symbol") or st.session_state.get("selected_ticker")
    
    if not current_ticker:
        render_page_header("Unternehmens-Detail", "Kein Unternehmen ausgewählt.")
        if st.button("Zurück zur Übersicht"):
            st.session_state["selected_company_symbol"] = None
            st.rerun()
        return

    # Header
    col_title, col_actions = st.columns([0.7, 0.3], vertical_alignment="center")
    with col_title:
        render_page_header(
            f"Unternehmen: {current_ticker}", 
            "Detaillierte Analyse des Unternehmensprofils und der Trade-Historie."
        )
    
    with col_actions:
        if st.button("← Zurück zur Übersicht", use_container_width=True):
            st.session_state["selected_company_symbol"] = None
            st.rerun()

    # Daten laden
    result = service.get_ticker_detail(current_ticker, accumulate=True)
    profile = result.company_profile or {}

    # 3. Intelligence Header
    st.subheader(f"{profile.get('company_name', 'N/A')} · {profile.get('sector', 'N/A')}")
    
    kpis = [
        {"label": "Gesamt-Score", "value": f"{result.metrics.get('overall_score', 0):.2f}"},
        {"label": "Klasse", "value": result.metrics.get('score_class', 'F')},
        {"label": "Gate", "value": result.metrics.get('overall_status', 'UNKNOWN')},
        {"label": "Trades", "value": format_number(result.metrics.get('trade_count'), "{:,.0f}")},
    ]
    from src.ui.components.page_scaffold import render_kpi_row
    render_kpi_row(kpis)

    st.markdown("---")

    # 4. Primary Insight Area (Breakdown & History)
    left, right = st.columns([0.6, 0.4])
    
    with left:
        st.subheader("Trade-Historie & Volumen")
        if result.rows:
            df = pd.DataFrame(result.rows)
            # Chart
            if 'transaction_date' in df.columns:
                df['transaction_date'] = pd.to_datetime(df['transaction_date'])
                chart_data = df.groupby('transaction_date')['accumulated_trade_value_estimated'].sum()
                st.line_chart(chart_data, height=300)
            
            # Tabelle
            st.caption("Letzte Transaktionen")
            render_trade_table(df.head(20), height=400)
        else:
            from src.ui.components.page_scaffold import render_empty_state
            render_empty_state("Keine Trades gefunden.")

    with right:
        st.subheader("Profil & Metriken")
        with st.container(border=True):
            st.write("**Sektor & Industrie**")
            st.write(f"**Sektor:** {profile.get('sector', 'N/A')}")
            st.write(f"**Industrie:** {profile.get('industry', 'N/A')}")
            
            st.markdown("---")
            st.write("**Marktkapitalisierung**")
            st.write(f"**Marktkap:** {format_mcap(profile.get('market_cap'), profile.get('currency', 'USD'))}")
            st.write(f"**Börse:** {profile.get('exchange_full_name', profile.get('exchange')) or 'Keine Angabe'}")
            
            st.markdown("---")
            st.write("**Gate & Scoring**")
            status = result.metrics.get('overall_status', 'UNKNOWN')
            status_badge(status, status_type=status)
            
            st.write(f"**Ø Score:** {result.metrics.get('overall_score', 0):.2f}")
            
            if status == "FAIL":
                st.error("Dieses Unternehmen erfüllt aktuell die Gate-Kriterien nicht.")
            
            st.markdown("---")
            if profile.get("website"):
                st.link_button("Unternehmens-Website", profile["website"], use_container_width=True)
            
            if profile.get("description"):
                with st.expander("Unternehmensbeschreibung"):
                    st.write(profile["description"])
