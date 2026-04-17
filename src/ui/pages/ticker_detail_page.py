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


def render_ticker_detail_page(service: AnalysisService) -> None:
    """Rendert den Company Intelligence Workspace."""
    
    # 1. Scope Selection & Navigation
    try:
        all_symbols = service.list_ticker_options()
    except Exception:
        all_symbols = []

    selected_symbol = st.session_state.get("selected_ticker")
    if not selected_symbol and all_symbols:
        selected_symbol = all_symbols[0]

    render_page_header(
        "Unternehmen", 
        "Company Intelligence Workspace & Trade Analyse.",
        actions=[{"label": "Vergleich aktivieren", "type": "secondary"}]
    )

    # 2. Workspace Scope (Context Bar)
    c1, c2 = st.columns([0.4, 0.6])
    with c1:
        current_ticker = st.selectbox("Symbol suchen", all_symbols, index=all_symbols.index(selected_symbol) if selected_symbol in all_symbols else 0)
        st.session_state["selected_ticker"] = current_ticker
    
    render_context_bar(
        active_filters=[f"Ticker: {current_ticker}"],
        mysql_target=st.session_state.get("mysql_runtime_target", "local")
    )

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
    render_kpi_row(kpis)

    st.markdown("---")

    # 4. Primary Insight Area (Breakdown & History)
    left, right = st.columns([0.6, 0.4])
    
    with left:
        st.subheader("Trade-Historie & Volumen")
        if result.rows:
            df = pd.DataFrame(result.rows)
            df['transaction_date'] = pd.to_datetime(df['transaction_date'])
            # Chart
            chart_data = df.groupby('transaction_date')['accumulated_trade_value_estimated'].sum()
            st.line_chart(chart_data, height=300)
            
            # Tabelle
            st.caption("Letzte Transaktionen")
            render_trade_table(df.head(10), height=350)
        else:
            render_empty_state("Keine Trades gefunden.")

    with right:
        st.subheader("Score & Gate Breakdown")
        with st.container(border=True):
            st.write("**Score Komponenten**")
            # Beispielhafte Aufschlüsselung (da Domain-Logik in Service liegt)
            st.progress(min(max(result.metrics.get('overall_score', 0) / 10, 0), 1.0), text=f"Value Score: {result.metrics.get('overall_score', 0):.1f}")
            st.caption("Basierend auf Volumen, Häufigkeit und Kursreaktion.")
            
            st.markdown("---")
            st.write("**Gate Analyse**")
            status = result.metrics.get('overall_status', 'UNKNOWN')
            status_badge(status, status_type=status)
            
            if status == "FAIL":
                st.error("Dieses Unternehmen erfüllt aktuell die Gate-Kriterien (z.B. Mindestumsatz, Rechtsform) nicht. Daher werden keine vertieften Profildaten von externen APIs geladen.")
            
            st.markdown("---")
            st.write("**Unternehmensprofil**")
            st.write(f"**Marktkap:** {format_mcap(profile.get('market_cap'), profile.get('currency', 'USD'))}")
            st.write(f"**Börse:** {profile.get('exchange_full_name', profile.get('exchange')) or 'Keine Angabe'}")
            if profile.get("website"):
                st.link_button("Website öffnen", profile["website"], use_container_width=True)
