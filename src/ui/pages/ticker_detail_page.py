"""Ticker-Detailseite mit Profil, Trades und Kennzahlen."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.services.analysis_service import AnalysisService
from src.ui.components.context_bar import render_context_bar
from src.ui.components.status_badges import gate_badge, score_class_badge, status_badge, validation_badge


def format_mcap(value: Any, currency: str = "USD") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return f"- {currency}"
    try:
        return f"{float(value):,.0f} {currency}"
    except (ValueError, TypeError):
        return f"- {currency}"


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
    """Rendert die Detailansicht für ein ausgewähltes Symbol."""
    st.title("Unternehmen")
    st.caption("Deep Dive: Profil, Trade-Historie und Score-Analyse.")

    try:
        all_symbols = service.list_ticker_options()
    except Exception:
        all_symbols = []

    default_index = 0
    selected_ticker_state = st.session_state.get("selected_ticker")
    if selected_ticker_state in all_symbols:
        default_index = all_symbols.index(selected_ticker_state)

    # 1. Header & Context
    c1, c2 = st.columns([0.4, 0.6])
    with c1:
        selected_symbol = st.selectbox("Symbol auswählen", all_symbols, index=default_index, label_visibility="collapsed")
    
    render_context_bar(
        active_filters=[f"Symbol: {selected_symbol}"] if selected_symbol else None,
        mysql_target=st.session_state.get("mysql_runtime_target", "local")
    )

    if not selected_symbol:
        st.info("Bitte wählen Sie ein Symbol aus dem Explorer oder der Liste.")
        return

    result = service.get_ticker_detail(selected_symbol, accumulate=True)
    profile = result.company_profile or {}

    # 2. Summary & Score Breakdown (Horizontal)
    st.subheader(f"{profile.get('company_name', selected_symbol)} ({selected_symbol})")
    
    score_val = result.metrics.get("overall_score", 0)
    score_class = result.metrics.get("score_class", "F")
    status = result.metrics.get("overall_status", "UNKNOWN")
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Gesamt-Score", f"{score_val:.2f}")
    with m2:
        st.write("**Bewertung**")
        score_class_badge(score_class)
    with m3:
        st.write("**Status**")
        status_badge(status, status_type=status)
    with m4:
        st.metric("Trades", format_number(result.metrics.get("trade_count"), "{:,.0f}"))

    st.markdown("---")

    # 3. Unternehmensdaten & Sektor
    col_info, col_desc = st.columns([0.4, 0.6])
    with col_info:
        st.markdown("#### Unternehmensdaten")
        st.write(f"**Sektor:** {profile.get('sector', '-')}")
        st.write(f"**Branche:** {profile.get('industry', '-')}")
        st.write(f"**Marktkap:** {format_mcap(profile.get('market_cap'), profile.get('currency', 'USD'))}")
        st.write(f"**Börse:** {profile.get('exchange_full_name', '-')}")
        if profile.get("website"):
            st.link_button("🌐 Website", profile["website"], use_container_width=True)
    
    with col_desc:
        st.markdown("#### Beschreibung")
        desc = profile.get('description')
        if desc and desc != "None":
            st.write(desc)
        else:
            st.info("Keine Beschreibung verfügbar.")

    st.markdown("---")

    # 4. Trade-Historie & Gate-Details
    tab_trades, tab_gate, tab_raw = st.tabs(["Trade Historie", "Gate Details", "Technische Daten"])
    
    with tab_trades:
        st.subheader("Insider Trades (Akkumuliert)")
        if not result.rows:
            st.info(f"Keine Transaktionen für {selected_symbol} gefunden.")
        else:
            df_display = pd.DataFrame(result.rows)
            # Spaltenbereinigung und Formatting hier (verkürzt für das Beispiel)
            display_cols = [
                "reporting_name", "direction", "accumulated_trade_value_estimated", 
                "score", "score_class", "gate_status", "transaction_date"
            ]
            st.dataframe(
                _safe_select_columns(df_display, display_cols),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "reporting_name": st.column_config.TextColumn("Insider", width="medium"),
                    "direction": st.column_config.TextColumn("Richtung", width="small"),
                    "accumulated_trade_value_estimated": st.column_config.NumberColumn("Trade Value", format="$%.2f", width="medium"),
                    "score": st.column_config.NumberColumn("Score", format="%.2f", width="small"),
                    "score_class": st.column_config.TextColumn("Klasse", width="small"),
                    "gate_status": st.column_config.TextColumn("Gate", width="small"),
                    "transaction_date": st.column_config.DateColumn("Datum", width="small"),
                }
            )

    with tab_gate:
        st.subheader("Gate-Analytik")
        gate_df = pd.DataFrame(result.rows)
        if not gate_df.empty and "gate_status" in gate_df.columns:
            gate_counts = gate_df["gate_status"].fillna("UNKNOWN").astype(str).str.upper().value_counts()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("PASS", int(gate_counts.get('PASS', 0)))
            c2.metric("PENDING", int(gate_counts.get('PENDING', 0)))
            c3.metric("FAIL", int(gate_counts.get('FAIL', 0)))
            
            failed = gate_df[gate_df["gate_status"].fillna("").astype(str).str.upper() == "FAIL"]
            if not failed.empty:
                st.markdown("**Ausschlussgründe**")
                st.dataframe(_safe_select_columns(failed, ["transaction_date", "reporting_name", "gate_reason"]), hide_index=True, use_container_width=True)

    with tab_raw:
        st.subheader("Rohdaten-Audit")
        if result.raw_rows:
            st.json(result.raw_rows[:3])
            st.download_button(
                "Rohdaten (JSON) laden",
                data=str(result.raw_rows),
                file_name=f"{selected_symbol}_raw.json",
                use_container_width=True
            )
        else:
            st.info("Keine Rohdaten für diesen Ticker hinterlegt.")
