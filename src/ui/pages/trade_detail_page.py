"""Trade-Detailseite (Requirement 5)."""

from __future__ import annotations
import streamlit as st
from src.services.analysis_service import AnalysisService
from src.services.database_status_service import DatabaseStatus
from src.ui.components.page_scaffold import render_page_header, render_empty_state, render_kpi_row


def _safe_text(value: object, fallback: str = "Nicht verfügbar") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return fallback if text == "" or text.lower() in {"nan", "none", "n/a"} else text


def _safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback

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
        f"{_safe_text(trade.get('symbol_at_trade'), fallback='–')} - {_safe_text(trade.get('reporting_name'), fallback='Unbekannter Insider')}",
        f"{_safe_text(trade.get('acquisition_or_disposition'), fallback='Unbekannt')} am {_safe_text(trade.get('transaction_date'))}"
    )

    # 1. KPI-Übersicht (Requirement 5.2)
    kpis = [
        {"label": "Wert", "value": f"${_safe_float(trade.get('trade_value_estimated')):,.0f}"},
        {"label": "Score", "value": f"{_safe_float(trade.get('score')):.1f}"},
        {"label": "Klasse", "value": _safe_text(trade.get("score_class"), fallback="Nicht verfügbar")},
    ]
    render_kpi_row(kpis)

    # 2. Sektionen (Requirement 5.2)
    c1, c2 = st.columns(2)
    
    with c1:
        with st.container(border=True):
            st.subheader("Trade-Informationen")
            st.write(f"**Symbol:** {_safe_text(trade.get('symbol_at_trade'), fallback='–')}")
            st.write(f"**Insider:** {_safe_text(trade.get('reporting_name'), fallback='Unbekannter Insider')}")
            st.write(f"**Rolle:** {_safe_text(trade.get('type_of_owner'))}")
            st.write(f"**Richtung:** {_safe_text(trade.get('acquisition_or_disposition'), fallback='Unbekannt')}")
            st.write(f"**Menge:** {_safe_float(trade.get('qty')):,.0f}")
            st.write(f"**Preis:** ${_safe_float(trade.get('price')):,.2f}")
            st.write(f"**Datum:** {_safe_text(trade.get('transaction_date'))}")
            st.write(f"**Filing:** {_safe_text(trade.get('filing_date'))}")

    with c2:
        with st.container(border=True):
            st.subheader("Status & Scoring")
            st.write("**Gate-Status:**", _safe_text(trade.get("gate_status")))
            st.write("**Gate-Begründung:**", trade.get("gate_reason") or "Nicht vorhanden")
            st.write("**Validierungsstatus:**", _safe_text(trade.get("validation_status")))
            st.write("**Dashboard-valide:**", "Ja" if trade.get("dashboard_valid") else "Nein")
            st.write("**Dedupe-Key:**", f"`{_safe_text(trade.get('dedupe_key'))}`")
            source_url = str(trade.get("source_url") or "").strip()
            if source_url:
                st.link_button("Originales SEC-Filing (externer Link)", source_url, help="Öffnet das Filing in einem neuen Browser-Tab.")
            else:
                st.caption("Kein Original-SEC-Filing für diesen Trade hinterlegt.")

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
