"""Trade-Detailseite (Requirement 5)."""

from __future__ import annotations
import pandas as pd
import streamlit as st
from src.services.accumulation_service import AccumulationService
from src.services.analysis_service import AnalysisService
from src.services.database_status_service import DatabaseStatus
from src.ui.components.page_scaffold import render_page_header, render_empty_state, render_kpi_row
from src.ui.components.tables import render_trade_table


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


def _aod_token(direction: object) -> str | None:
    normalized = str(direction or "").strip().upper()
    if normalized == "BUY":
        return "A"
    if normalized == "SELL":
        return "D"
    return None


def _to_date(value: object) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed


def _render_group_trade_detail(service: AnalysisService, group_context: dict[str, object]) -> bool:
    symbol = str(group_context.get("symbol_at_trade") or "").strip()
    reporting_name = str(group_context.get("reporting_name") or "").strip()
    group_id = str(group_context.get("accumulation_group_id") or "").strip()
    direction = str(group_context.get("direction") or "").strip().upper()
    date_from = _to_date(group_context.get("accumulation_start_date"))
    date_to = _to_date(group_context.get("accumulation_end_date"))

    if not symbol:
        return False

    filters: dict[str, object] = {"symbol": symbol}
    if reporting_name:
        filters["reporting_name"] = reporting_name
    if date_from is not None:
        filters["date_from"] = date_from.date()
    if date_to is not None:
        filters["date_to"] = date_to.date()
    aod = _aod_token(direction)
    if aod:
        filters["acquisition_or_disposition"] = aod

    with st.spinner("Lade Einzeltrades der Akkumulationsgruppe..."):
        try:
            trades = service.trade_repo.fetch_trades(filters=filters, limit=2000)
        except Exception as exc:
            st.error(f"Fehler beim Laden der Gruppentrades: {exc}")
            return True

    if trades.empty:
        render_empty_state("Für diese Akkumulationsgruppe wurden keine Einzeltrades gefunden.")
        return True

    grouped = AccumulationService.tag_trades_with_groups(trades.copy(), window_days=3)
    if group_id and "accumulation_group_id" in grouped.columns:
        selected = grouped[grouped["accumulation_group_id"].astype(str) == group_id].copy()
        if selected.empty:
            selected = grouped
    else:
        selected = grouped

    selected = selected.sort_values("transaction_date", ascending=False, na_position="last").reset_index(drop=True)
    total_value = pd.to_numeric(selected.get("trade_value_estimated"), errors="coerce").fillna(0).sum()
    avg_score = pd.to_numeric(selected.get("score"), errors="coerce").mean()

    render_page_header(
        f"{symbol} - Akkumulationsgruppe",
        f"{reporting_name or 'Unbekannter Insider'} · {direction or 'UNKNOWN'}",
    )
    render_kpi_row([
        {"label": "Einzeltrades", "value": str(len(selected))},
        {"label": "Gruppenwert", "value": f"${float(total_value):,.0f}"},
        {"label": "Ø Score", "value": f"{float(avg_score):.1f}" if pd.notna(avg_score) else "-"},
    ])

    st.markdown("### Einzeltrades in dieser Gruppe")
    render_trade_table(selected, height=480, on_select="ignore")
    if st.button("Zurück zur Übersicht", use_container_width=True, key="back_from_group_detail"):
        st.session_state["nav_target"] = "Dashboard"
        st.rerun()
    return True

def render_trade_detail_page(service: AnalysisService | None, dedupe_key: str | None = None, db_status: DatabaseStatus | None = None) -> None:
    """Rendert die Detailseite für einen einzelnen Trade."""
    if service is None:
        render_empty_state("Trade-Details sind derzeit nicht verfügbar, da die Analyse-Datenbank offline ist.")
        return

    # Dedupe-Key ist die authoritative Quelle
    if not dedupe_key:
        dedupe_key = st.session_state.get("selected_trade_key")

    dedupe_key = str(dedupe_key or "").strip() if dedupe_key else None

    # Fallback fuer Dashboard-Drilldown auf Akkumulationsgruppen.
    group_context = st.session_state.get("selected_trade_group")
    if not dedupe_key and isinstance(group_context, dict):
        handled = _render_group_trade_detail(service, group_context)
        if handled:
            return

    if not dedupe_key:
        render_empty_state("Kein Trade ausgewählt.")
        if st.button("Zurück zur Trades-Übersicht"):
            st.session_state["nav_target"] = "Trades"
            st.rerun()
        return

    # Daten laden
    with st.spinner("Lade Trade-Details..."):
        try:
            trades = service.trade_repo.fetch_trades(filters={"dedupe_key": dedupe_key}, limit=1)
        except Exception as e:
            st.error(f"Fehler beim Laden des Trades: {str(e)[:100]}")
            if st.button("Zurück zur Trades-Übersicht"):
                st.session_state["nav_target"] = "Trades"
                st.rerun()
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
    gate_status = _safe_text(trade.get("gate_status"), fallback="Nicht verfügbar")
    score_val = _safe_float(trade.get("score"), fallback=0.0)
    score_class = _safe_text(trade.get("score_class"), fallback="Nicht verfügbar")

    kpis = [
        {"label": "Wert", "value": f"${_safe_float(trade.get('trade_value_estimated')):,.0f}"},
        {"label": "Score", "value": f"{score_val:.1f}"},
        {"label": "Gate", "value": gate_status},
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

    with c2:
        with st.container(border=True):
            st.subheader("Status & Analyse")
            st.write("**Gate-Status:**", gate_status)
            gate_reason = trade.get("gate_reason") or ""
            if gate_reason:
                st.write("**Gate-Grund:**", str(gate_reason).strip())
            st.write("**Validierung:**", _safe_text(trade.get("validation_status")))
            st.write("**Klasse:**", score_class)
            source_url = str(trade.get("source_url") or "").strip()
            if source_url:
                st.link_button("SEC-Filing (extern)", source_url, help="Öffnet das Filing in einem neuen Browser-Tab.")

    breakdown_fields = {
        "Core-Insider": trade.get("core_insider_score"),
        "Investability": trade.get("investability_score"),
        "Execution": trade.get("execution_score"),
        "TR-Score": trade.get("trade_republic_score"),
        "Final-Score": trade.get("final_score"),
        "Decision": trade.get("decision_status"),
        "Final-Klasse": trade.get("final_class"),
    }
    visible_breakdown = {k: v for k, v in breakdown_fields.items() if v not in (None, "", "nan")}
    if visible_breakdown:
        with st.expander("Scoring-Breakdown", expanded=False):
            for label, value in visible_breakdown.items():
                st.write(f"**{label}:** {value}")

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
