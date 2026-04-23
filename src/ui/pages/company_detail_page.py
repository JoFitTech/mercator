"""Unternehmens-Detailseite (Requirement 7)."""

from __future__ import annotations
import streamlit as st
import pandas as pd
from src.services.analysis_service import AnalysisService
from src.services.database_status_service import DatabaseStatus
from src.ui.components.page_scaffold import render_page_header, render_empty_state, render_kpi_row
from src.ui.components.tables import get_single_selected_row_index, render_trade_table


def _safe_text(value: object, fallback: str = "Nicht verfügbar") -> str:
    if value is None or pd.isna(value):
        return fallback
    text = str(value).strip()
    return fallback if text == "" or text.lower() in {"nan", "none", "n/a"} else text


def _format_market_cap(value: object) -> str:
    if value is None or pd.isna(value):
        return "Nicht verfügbar"
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "Nicht verfügbar"


def render_company_detail_page(service: AnalysisService | None, symbol: str | None = None, db_status: DatabaseStatus | None = None) -> None:
    """Rendert die Detailseite für ein Unternehmen."""
    if service is None:
        render_empty_state("Unternehmensdetails sind derzeit nicht verfügbar, da die Analyse-Datenbank offline ist.")
        return

    if not symbol:
        symbol = st.session_state.get("selected_company_symbol")

    symbol = str(symbol or "").strip() if symbol else None

    if not symbol:
        render_empty_state("Kein Unternehmen ausgewählt.")
        if st.button("Zurück zur Unternehmen-Übersicht"):
            st.session_state["nav_target"] = "Unternehmen"
            st.rerun()
        return

    # Daten laden
    with st.spinner(f"Lade Details für {symbol}..."):
        try:
            result = service.get_ticker_detail(symbol, accumulate=False)
        except Exception as e:
            st.error(f"Fehler beim Laden der Unternehmensdaten: {str(e)[:100]}")
            if st.button("Zurück zur Übersicht"):
                st.session_state["nav_target"] = "Unternehmen"
                st.rerun()
            return

    if not result or result.rows is None:
        render_empty_state(f"Keine Daten für '{symbol}' gefunden.")
        return

    # Header
    profile = result.company_profile or {}
    render_page_header(
        f"{symbol} - {_safe_text(profile.get('company_name'), fallback=symbol)}",
        f"{_safe_text(profile.get('sector'))} | {_safe_text(profile.get('industry'))} | {_safe_text(profile.get('country'))}"
    )

    # 1. KPIs (Requirement 7.2)
    metrics = result.metrics or {}
    kpis = [
        {"label": "Marktkapitalisierung", "value": _format_market_cap(profile.get("market_cap"))},
        {"label": "Anzahl Trades", "value": str(metrics.get("trade_count", 0))},
        {"label": "Durchschn. Score", "value": f"{metrics.get('overall_score', 0):.1f}"},
        {"label": "Gesamtstatus", "value": _safe_text(metrics.get("overall_status"))},
    ]
    render_kpi_row(kpis)

    # 2. Profil-Sektion
    with st.expander("Unternehmensprofil & Beschreibung", expanded=False):
        st.write(_safe_text(profile.get("description"), fallback="Kein Profil"))
        if profile.get("website"):
            st.link_button("Website besuchen", profile.get("website"))

    # 3. Trade-Historie (Requirement 7.2)
    st.markdown("---")
    st.subheader("Insider Trade-Historie")
    st.caption("Sortierung: Neueste Trades zuerst. Wählen Sie eine Zeile für Detailaktionen.")
    trades_df = pd.DataFrame(result.rows) if result.rows else pd.DataFrame()
    if trades_df.empty:
        st.info("Keine Trades in der Historie gefunden.")
    else:
        if "transaction_date" in trades_df.columns:
            trades_df["transaction_date"] = pd.to_datetime(trades_df["transaction_date"], errors="coerce")
            trades_df = trades_df.sort_values("transaction_date", ascending=False, na_position="last").reset_index(drop=True)
        event = render_trade_table(trades_df, height=500)
        selected_idx = get_single_selected_row_index(event, len(trades_df))
        if selected_idx is not None:
            try:
                selected_trade = trades_df.iloc[selected_idx]
            except (IndexError, KeyError):
                st.error("Ausgewählte Zeile ist ungültig. Bitte erneut auswählen.")
            else:
                with st.container(border=True):
                    st.markdown("**Ausgewählt:** Trade-Historienzeile")
                    if st.button("Trade-Detail öffnen", type="primary", use_container_width=True):
                        st.session_state["selected_trade_key"] = selected_trade.get("dedupe_key")
                        st.session_state["nav_target"] = "Trade-Detail"
                        st.rerun()
        else:
            st.info("Bitte eine Zeile auswählen, um in den Trade-Detailmodus zu wechseln.")

    # Zurück Button
    if st.button("Zurück zur Übersicht", use_container_width=True):
        st.session_state["nav_target"] = "Unternehmen"
        st.rerun()
