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
from src.ui.components.tables import get_single_selected_row_index, render_trade_table

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
TRADE_PAGE_SIZES = [50, 100, 200]


def _trade_filter_widget_keys() -> dict[str, str]:
    return {
        "symbol": "trades_filter_symbol",
        "reporting_name": "trades_filter_reporting_name",
        "direction": "trades_filter_direction",
        "gate_status": "trades_filter_gate_status",
        "validation_status": "trades_filter_validation_status",
        "date_range": "trades_filter_date_range",
        "min_score": "trades_filter_min_score",
        "min_value": "trades_filter_min_value",
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
    if isinstance(date_range, date):
        normalized["date_range"] = (date_range, date_range)
    elif isinstance(date_range, (list, tuple)) and len(date_range) > 0:
        date_from = date_range[0] if isinstance(date_range[0], date) else TRADE_FILTER_DEFAULTS["date_range"][0]
        second = date_range[1] if len(date_range) > 1 else date_from
        date_to = second if isinstance(second, date) else date_from
        normalized["date_range"] = (date_from, date_to) if date_to >= date_from else (date_to, date_from)
    else:
        normalized["date_range"] = TRADE_FILTER_DEFAULTS["date_range"]
    normalized["min_score"] = int(normalized.get("min_score") or 0)
    normalized["min_value"] = int(normalized.get("min_value") or 0)
    return normalized


def _sync_trade_filter_widgets_from_state(force: bool = False) -> None:
    """Synchronisiert Widget-State aus dem kanonischen Filter-State."""
    active_filters = _normalize_trades_filters(st.session_state.get("trades_filters"))
    st.session_state["trades_filters"] = active_filters
    for field, key in _trade_filter_widget_keys().items():
        if force or key not in st.session_state:
            st.session_state[key] = active_filters[field]


def _read_trade_filters_from_widgets() -> dict:
    """Liest den vollständigen Filterzustand aus den Widgets."""
    keys = _trade_filter_widget_keys()
    return _normalize_trades_filters({
        "symbol": str(st.session_state.get(keys["symbol"], "")).strip(),
        "reporting_name": str(st.session_state.get(keys["reporting_name"], "")).strip(),
        "direction": st.session_state.get(keys["direction"], "Alle"),
        "gate_status": st.session_state.get(keys["gate_status"], "Alle"),
        "validation_status": st.session_state.get(keys["validation_status"], "Alle"),
        "date_range": st.session_state.get(keys["date_range"], TRADE_FILTER_DEFAULTS["date_range"]),
        "min_score": st.session_state.get(keys["min_score"], 0),
        "min_value": st.session_state.get(keys["min_value"], 0),
    })


def _reset_trade_filters_and_widgets() -> None:
    """Setzt kanonischen Filter-State und Widget-State vollständig zurück."""
    st.session_state["trades_filters"] = dict(TRADE_FILTER_DEFAULTS)
    _sync_trade_filter_widgets_from_state(force=True)


def _trade_action_symbol_label(trade_row: pd.Series) -> str:
    symbol = str(trade_row.get("symbol_at_trade") or "").strip()
    if symbol and symbol.lower() != "nan":
        return symbol
    return "Unbekanntes Symbol"


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
        st.session_state["trades_filters"] = dict(TRADE_FILTER_DEFAULTS)
    st.session_state["trades_filters"] = _normalize_trades_filters(st.session_state["trades_filters"])
    _sync_trade_filter_widgets_from_state()

    with st.expander("Filter und Suche", expanded=True):
        with st.form("trades_filters_form", clear_on_submit=False):
            f1, f2, f3 = st.columns(3)
            f1.text_input("Symbol", key="trades_filter_symbol", help="Ticker-Symbol (z.B. AAPL)")
            f2.text_input("Insider-Name", key="trades_filter_reporting_name", help="Name des Insiders")
            f3.selectbox("Richtung", options=["Alle", "BUY", "SELL"], key="trades_filter_direction")

            f4, f5, f6 = st.columns(3)
            f4.selectbox("Gate-Status", options=["Alle", "PASS", "PENDING", "FAIL"], key="trades_filter_gate_status")
            f5.selectbox("Validierungsstatus", options=["Alle", "VALID", "INVALID"], key="trades_filter_validation_status")
            f6.date_input("Zeitraum (Transaktionsdatum)", key="trades_filter_date_range")

            f7, f8 = st.columns(2)
            f7.slider("Min. Score", 0, 100, key="trades_filter_min_score")
            f8.number_input("Min. Wert ($)", step=10000, key="trades_filter_min_value")

            apply_pressed = st.form_submit_button("Filter anwenden", type="primary", use_container_width=True)
        _, b2 = st.columns(2)
        if apply_pressed:
            st.session_state["trades_filters"] = _read_trade_filters_from_widgets()
            st.rerun()
        if b2.button("Filter zurücksetzen", use_container_width=True, key="trades_reset_filters"):
            _reset_trade_filters_and_widgets()
            st.rerun()
            return

    # 2. Daten laden
    active_filters = _normalize_trades_filters(st.session_state["trades_filters"])
    st.session_state["trades_filters"] = active_filters
    filters = _build_query_filters(active_filters)
    render_filter_chip_bar(
        active_filters={
            "Symbol": filters.get("symbol") or "Alle",
            "Insider": filters.get("reporting_name") or "Alle",
            "Richtung": active_filters["direction"],
            "Gate": active_filters["gate_status"],
            "Validierung": active_filters["validation_status"],
            "Zeitraum": f"{filters.get('date_from')} bis {filters.get('date_to')}",
            "Min. Score": active_filters["min_score"],
            "Min. Wert": f"${active_filters['min_value']:,}",
        }
    )
    summarize_filters("Aktive Filter", {
        "Symbol": filters.get("symbol"),
        "Insider": filters.get("reporting_name"),
        "Richtung": active_filters["direction"],
        "Gate": active_filters["gate_status"],
        "Validierung": active_filters["validation_status"],
    })

    p1, p2 = st.columns([1, 1])
    page_size = p1.selectbox("Seitengröße", options=TRADE_PAGE_SIZES, index=1, key="trades_page_size")
    current_page = max(1, int(p2.number_input("Seite", min_value=1, value=1, step=1, key="trades_current_page")))
    offset = (current_page - 1) * int(page_size)

    with st.spinner("Lade Trades..."):
        (trades_df, total_rows), load_error = safe_service_call(lambda: service.get_filtered_trades_page(
            filters=filters,
            limit=int(page_size),
            offset=offset,
            min_value=active_filters["min_value"],
        ), context_label="Trades", fallback=(pd.DataFrame(), 0))
    if load_error is not None:
        st.warning("Die Trades-Ansicht bleibt bedienbar, aber Daten konnten gerade nicht geladen werden.")
        return

    if trades_df.empty:
        render_empty_state("Keine Trades für die aktuellen Filter gefunden.")
        st.caption("Nächster Schritt: Filter zurücksetzen oder Zeitraum erweitern.")
        c1, c2 = st.columns(2)
        if c1.button("Filter zurücksetzen", key="trades_empty_reset", use_container_width=True):
            _reset_trade_filters_and_widgets()
            st.rerun()
        if c2.button("Zeitraum auf 90 Tage setzen", key="trades_empty_expand_period", use_container_width=True):
            st.session_state["trades_filters"] = _normalize_trades_filters(st.session_state.get("trades_filters"))
            st.session_state["trades_filters"]["date_range"] = TRADE_FILTER_DEFAULTS["date_range"]
            _sync_trade_filter_widgets_from_state(force=True)
            st.rerun()
        return

    total_pages = max(1, (int(total_rows) + int(page_size) - 1) // int(page_size))
    st.caption(f"Seite {current_page} von {total_pages} · Gesamt {total_rows} Treffer")

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
    trades_df = trades_df.copy()
    if "transaction_date" in trades_df.columns:
        trades_df["transaction_date"] = pd.to_datetime(trades_df["transaction_date"], errors="coerce")
        trades_df = trades_df.sort_values("transaction_date", ascending=False, na_position="last").reset_index(drop=True)
    event = render_trade_table(trades_df, height=600)
    st.caption(
        "Sortierung: standardmäßig nach Datum (neueste zuerst). "
        "Sie können zusätzlich über Spaltenüberschriften sortieren."
    )
    st.caption("Auswahl-Flow: 1) Zeile markieren 2) Aktion im Bereich darunter ausführen.")

    selected_idx = get_single_selected_row_index(event, len(trades_df))
    if selected_idx is not None:
        selected_trade = trades_df.iloc[selected_idx]
        symbol_label = _trade_action_symbol_label(selected_trade)
        symbol_value = str(selected_trade.get("symbol_at_trade") or "").strip()
        can_open_company = bool(symbol_value) and symbol_value.lower() not in {"nan", "none"}
        with st.container(border=True):
            st.markdown(f"**Ausgewählt:** {symbol_label}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button(f"Trade-Detail öffnen: {symbol_label}", type="primary", use_container_width=True, key=f"open_trade_detail_{selected_idx}"):
                    st.session_state["selected_trade_key"] = selected_trade.get("dedupe_key")
                    st.session_state["nav_target"] = "Trade-Detail"
                    st.rerun()
            with c2:
                if st.button(
                    f"Unternehmens-Detail öffnen: {symbol_label}",
                    use_container_width=True,
                    disabled=not can_open_company,
                    key=f"open_company_detail_{selected_idx}",
                    help="Navigation benötigt ein gültiges Symbol." if not can_open_company else None,
                ):
                    st.session_state["selected_company_symbol"] = symbol_value
                    st.session_state["nav_target"] = "Unternehmens-Detail"
                    st.rerun()
    else:
        st.info("Bitte eine Zeile markieren, damit die Detail-Aktionen aktiv werden.")
