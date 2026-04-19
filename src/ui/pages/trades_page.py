"""Trades-Seite als operative Hauptarbeitsfläche (Requirement 4)."""

from __future__ import annotations
import pandas as pd
import streamlit as st
from datetime import date, timedelta
from src.services.analysis_service import AnalysisService
from src.ui.components.context_bar import render_filter_chip_bar
from src.ui.components.page_scaffold import render_kpi_row, render_page_header, render_empty_state
from src.ui.components.tables import render_trade_table

def render_trades_page(service: AnalysisService) -> None:
    """Rendert die Trades-Seite."""
    render_page_header("Trades", "Operative Arbeitsfläche für Insider-Trades.")

    # 1. Filterleiste (Requirement 4.2)
    if "trades_filters" not in st.session_state:
        st.session_state.trades_filters = {
            "symbol": "",
            "reporting_name": "",
            "direction": "Alle",
            "gate_status": "Alle",
            "validation_status": "Alle",
            "date_range": (date.today() - timedelta(days=90), date.today()),
            "min_score": 0,
            "min_value": 0
        }

    with st.expander("🔍 Filter & Suche", expanded=True):
        f1, f2, f3 = st.columns(3)
        symbol = f1.text_input("Symbol", value=st.session_state.trades_filters["symbol"], help="Ticker-Symbol (z.B. AAPL)")
        reporting_name = f2.text_input("Reporting Name", value=st.session_state.trades_filters["reporting_name"], help="Name des Insiders")
        direction = f3.selectbox("Richtung", options=["Alle", "BUY", "SELL"], index=0 if st.session_state.trades_filters["direction"] == "Alle" else (1 if st.session_state.trades_filters["direction"] == "BUY" else 2))

        f4, f5, f6 = st.columns(3)
        gate_status = f4.selectbox("Gate Status", options=["Alle", "PASS", "PENDING", "FAIL"], index=0)
        val_status = f5.selectbox("Validation Status", options=["Alle", "VALID", "INVALID"], index=0)
        date_range = f6.date_input("Zeitraum (transaction_date)", value=st.session_state.trades_filters["date_range"])

        f7, f8 = st.columns(2)
        min_score = f7.slider("Min. Score", 0, 100, int(st.session_state.trades_filters["min_score"]))
        min_value = f8.number_input("Min. Wert ($)", value=int(st.session_state.trades_filters["min_value"]), step=10000)

        if st.button("Filter anwenden", type="primary", use_container_width=True):
            st.session_state.trades_filters.update({
                "symbol": symbol,
                "reporting_name": reporting_name,
                "direction": direction,
                "gate_status": gate_status,
                "validation_status": val_status,
                "date_range": date_range,
                "min_score": min_score,
                "min_value": min_value
            })
            st.rerun()

    # 2. Daten laden
    filters = {
        "symbol": st.session_state.trades_filters["symbol"] if st.session_state.trades_filters["symbol"] else None,
        "reporting_name": st.session_state.trades_filters["reporting_name"] if st.session_state.trades_filters["reporting_name"] else None,
        "gate_status": st.session_state.trades_filters["gate_status"] if st.session_state.trades_filters["gate_status"] != "Alle" else None,
        "validation_status": st.session_state.trades_filters["validation_status"] if st.session_state.trades_filters["validation_status"] != "Alle" else None,
        "date_from": st.session_state.trades_filters["date_range"][0] if len(st.session_state.trades_filters["date_range"]) > 0 else None,
        "date_to": st.session_state.trades_filters["date_range"][1] if len(st.session_state.trades_filters["date_range"]) > 1 else None,
        "min_score": st.session_state.trades_filters["min_score"],
    }
    
    if st.session_state.trades_filters["direction"] == "BUY":
        filters["acquisition_or_disposition"] = "A"
    elif st.session_state.trades_filters["direction"] == "SELL":
        filters["acquisition_or_disposition"] = "D"

    with st.spinner("Lade Trades..."):
        trades_df = service.get_filtered_trades(
            filters=filters,
            limit=1000,
            accumulate=False, # In der Hauptarbeitsfläche zeigen wir Roh-Trades
            min_value=st.session_state.trades_filters["min_value"]
        )

    if trades_df.empty:
        render_empty_state("Keine Trades gefunden.")
        return

    # 3. KPIs
    kpis = [
        {"label": "Treffer", "value": str(len(trades_df))},
        {"label": "Ø Score", "value": f"{trades_df['score'].mean():.1f}" if "score" in trades_df.columns else "-"},
        {"label": "Summe Volumen", "value": f"${trades_df['trade_value_estimated'].sum():,.0f}" if "trade_value_estimated" in trades_df.columns else "-"},
    ]
    render_kpi_row(kpis)

    # 4. Tabelle (Requirement 4.3: Spaltenpriorität)
    st.subheader("Trade-Explorer")
    
    # Detail-Button Logik via AgGrid Auswahl
    event = render_trade_table(trades_df, height=600)
    
    if event and event.get("selection") and event["selection"].get("rows"):
        selected_idx = event["selection"]["rows"][0]
        selected_trade = trades_df.iloc[selected_idx]
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button(f"🔍 Detail öffnen: {selected_trade.get('symbol_at_trade')}", type="primary", use_container_width=True):
                st.session_state["selected_trade_key"] = selected_trade.get("dedupe_key")
                st.session_state["nav_target"] = "Trade-Detail"
                st.rerun()
        with c2:
            if st.button(f"🏢 Unternehmen: {selected_trade.get('symbol_at_trade')}", use_container_width=True):
                st.session_state["selected_company_symbol"] = selected_trade.get("symbol_at_trade")
                st.session_state["nav_target"] = "Unternehmens-Detail"
                st.rerun()
    else:
        st.info("💡 Tipp: Wählen Sie einen Trade aus der Tabelle aus, um Details anzuzeigen.")
