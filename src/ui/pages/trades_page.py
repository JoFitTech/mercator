"""Trades-Seite als operative Hauptarbeitsfläche (Requirement 4)."""

from __future__ import annotations
import pandas as pd
import streamlit as st
from datetime import date, timedelta
from src.services.analysis_service import AnalysisService
from src.services.database_status_service import DatabaseStatus
from src.ui.components.context_bar import render_filter_chip_bar
from src.ui.components.page_scaffold import (
    render_kpi_row,
    render_page_header,
    render_empty_state,
    safe_service_call,
    summarize_filters,
)
from src.ui.components.tables import render_trade_table

TRADE_FILTER_DEFAULTS = {
    "symbol": "",
    "reporting_name": "",
    "direction": "Alle",
    "gate_status": "Alle",
    "validation_status": "Alle",
    "date_range": (date.today() - timedelta(days=90), date.today()),
    "min_score": 0,
    "min_value": 0,
}


def _normalize_trades_filters(filters: dict | None) -> dict:
    """Harmonisiert Session-Filter robust auf valide UI-Werte."""
    normalized = dict(TRADE_FILTER_DEFAULTS)
    if filters:
        normalized.update(filters)
    if normalized.get("direction") not in {"Alle", "BUY", "SELL"}:
        normalized["direction"] = "Alle"
    if normalized.get("gate_status") not in {"Alle", "PASS", "PENDING", "FAIL"}:
        normalized["gate_status"] = "Alle"
    if normalized.get("validation_status") not in {"Alle", "VALID", "INVALID"}:
        normalized["validation_status"] = "Alle"
    date_range = normalized.get("date_range")
    if not isinstance(date_range, (list, tuple)) or len(date_range) < 2:
        normalized["date_range"] = TRADE_FILTER_DEFAULTS["date_range"]
    normalized["min_score"] = int(normalized.get("min_score") or 0)
    normalized["min_value"] = int(normalized.get("min_value") or 0)
    return normalized


def _build_query_filters(active_filters: dict) -> dict:
    """Erzeugt deterministische Repository-Filter aus dem UI-State."""
    date_range = active_filters.get("date_range") or ()
    filters = {
        "symbol": (active_filters.get("symbol") or "").strip() or None,
        "reporting_name": (active_filters.get("reporting_name") or "").strip() or None,
        "gate_status": active_filters.get("gate_status") if active_filters.get("gate_status") != "Alle" else None,
        "validation_status": active_filters.get("validation_status") if active_filters.get("validation_status") != "Alle" else None,
        "date_from": date_range[0] if len(date_range) > 0 else None,
        "date_to": date_range[1] if len(date_range) > 1 else None,
        "min_score": int(active_filters.get("min_score") or 0),
    }
    direction = active_filters.get("direction")
    if direction == "BUY":
        filters["acquisition_or_disposition"] = "A"
    elif direction == "SELL":
        filters["acquisition_or_disposition"] = "D"
    return filters


def render_trades_page(service: AnalysisService | None, db_status: DatabaseStatus | None = None) -> None:
    """Rendert die Trades-Seite."""
    render_page_header("Trades", "Operative Arbeitsfläche für Insider-Trades.")
    if service is None:
        st.warning(
            "Trades können derzeit nicht geladen werden, da die Analyse-Datenbank nicht verfügbar ist."
        )
        return

    # 1. Filterleiste (Requirement 4.2)
    if "trades_filters" not in st.session_state:
        st.session_state.trades_filters = dict(TRADE_FILTER_DEFAULTS)
    st.session_state.trades_filters = _normalize_trades_filters(st.session_state.trades_filters)
    active_filters = st.session_state.trades_filters

    with st.expander("Filter und Suche", expanded=True):
        f1, f2, f3 = st.columns(3)
        symbol = f1.text_input("Symbol", value=active_filters["symbol"], key="trades_filter_symbol", help="Ticker-Symbol (z.B. AAPL)")
        reporting_name = f2.text_input("Insider-Name", value=active_filters["reporting_name"], key="trades_filter_reporting_name", help="Name des Insiders")
        direction = f3.selectbox("Richtung", options=["Alle", "BUY", "SELL"], key="trades_filter_direction", index=["Alle", "BUY", "SELL"].index(active_filters["direction"]))

        f4, f5, f6 = st.columns(3)
        gate_status = f4.selectbox("Gate-Status", options=["Alle", "PASS", "PENDING", "FAIL"], key="trades_filter_gate_status", index=["Alle", "PASS", "PENDING", "FAIL"].index(active_filters["gate_status"]))
        val_status = f5.selectbox("Validierungsstatus", options=["Alle", "VALID", "INVALID"], key="trades_filter_validation_status", index=["Alle", "VALID", "INVALID"].index(active_filters["validation_status"]))
        date_range = f6.date_input("Zeitraum (Transaktionsdatum)", value=active_filters["date_range"], key="trades_filter_date_range")

        f7, f8 = st.columns(2)
        min_score = f7.slider("Min. Score", 0, 100, int(active_filters["min_score"]), key="trades_filter_min_score")
        min_value = f8.number_input("Min. Wert ($)", value=int(active_filters["min_value"]), step=10000, key="trades_filter_min_value")

        b1, b2 = st.columns(2)
        if b1.button("Filter anwenden", type="primary", use_container_width=True, key="trades_apply_filters"):
            st.session_state.trades_filters.update({
                "symbol": symbol.strip(),
                "reporting_name": reporting_name.strip(),
                "direction": direction,
                "gate_status": gate_status,
                "validation_status": val_status,
                "date_range": date_range,
                "min_score": int(min_score),
                "min_value": int(min_value),
            })
            st.rerun()
        if b2.button("Filter zurücksetzen", use_container_width=True, key="trades_reset_filters"):
            st.session_state.trades_filters = dict(TRADE_FILTER_DEFAULTS)
            st.rerun()

    # 2. Daten laden
    filters = _build_query_filters(st.session_state.trades_filters)
    render_filter_chip_bar(
        active_filters={
            "Symbol": filters.get("symbol") or "Alle",
            "Insider": filters.get("reporting_name") or "Alle",
            "Richtung": st.session_state.trades_filters["direction"],
            "Gate": st.session_state.trades_filters["gate_status"],
            "Validierung": st.session_state.trades_filters["validation_status"],
            "Zeitraum": f"{filters.get('date_from')} bis {filters.get('date_to')}",
            "Min. Score": st.session_state.trades_filters["min_score"],
            "Min. Wert": f"${st.session_state.trades_filters['min_value']:,}",
        }
    )
    summarize_filters("Aktive Filter", {
        "Symbol": filters.get("symbol"),
        "Insider": filters.get("reporting_name"),
        "Richtung": st.session_state.trades_filters["direction"],
        "Gate": st.session_state.trades_filters["gate_status"],
        "Validierung": st.session_state.trades_filters["validation_status"],
    })

    with st.spinner("Lade Trades..."):
        trades_df, load_error = safe_service_call(lambda: service.get_filtered_trades(
            filters=filters,
            limit=1000,
            accumulate=False, # In der Hauptarbeitsfläche zeigen wir Roh-Trades
            min_value=st.session_state.trades_filters["min_value"],
        ), context_label="Trades", fallback=pd.DataFrame())
    if load_error is not None:
        st.warning("Die Trades-Ansicht bleibt bedienbar, aber Daten konnten gerade nicht geladen werden.")
        return

    if trades_df.empty:
        render_empty_state("Keine Trades für die aktuellen Filter gefunden.")
        st.caption("Nächster Schritt: Filter zurücksetzen oder Zeitraum erweitern.")
        c1, c2 = st.columns(2)
        if c1.button("Filter zurücksetzen", key="trades_empty_reset", use_container_width=True):
            st.session_state.trades_filters = dict(TRADE_FILTER_DEFAULTS)
            st.rerun()
        if c2.button("Zeitraum auf 90 Tage setzen", key="trades_empty_expand_period", use_container_width=True):
            st.session_state.trades_filters["date_range"] = TRADE_FILTER_DEFAULTS["date_range"]
            st.rerun()
        return

    # 3. KPIs
    kpis = [
        {"label": "Treffer", "value": str(len(trades_df))},
        {"label": "Ø Score", "value": f"{trades_df['score'].mean():.1f}" if "score" in trades_df.columns else "-"},
        {"label": "Summe Volumen", "value": f"${trades_df['trade_value_estimated'].sum():,.0f}" if "trade_value_estimated" in trades_df.columns else "-"},
    ]
    render_kpi_row(kpis)

    # 4. Tabelle (Requirement 4.3: Spaltenpriorität)
    st.subheader("Trades-Arbeitsfläche")
    
    # Detail-Button Logik via AgGrid Auswahl
    event = render_trade_table(trades_df, height=600)
    st.caption("Sortierung: Neueste Transaktionsdaten zuerst. Tabelle ist einzeilig auswählbar.")
    
    if event and event.get("selection") and event["selection"].get("rows"):
        selected_idx = event["selection"]["rows"][0]
        selected_trade = trades_df.iloc[selected_idx]
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button(f"Detail öffnen: {selected_trade.get('symbol_at_trade')}", type="primary", use_container_width=True):
                st.session_state["selected_trade_key"] = selected_trade.get("dedupe_key")
                st.session_state["nav_target"] = "Trade-Detail"
                st.rerun()
        with c2:
            if st.button(f"Unternehmen: {selected_trade.get('symbol_at_trade')}", use_container_width=True):
                st.session_state["selected_company_symbol"] = selected_trade.get("symbol_at_trade")
                st.session_state["nav_target"] = "Unternehmens-Detail"
                st.rerun()
    else:
        st.info("Hinweis: Wählen Sie einen Trade aus der Tabelle aus, um Details anzuzeigen.")
