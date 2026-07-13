"""Watchlist-Seite fuer die erste Stock-Analysis-MVP-Stufe."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.services.database_status_service import DatabaseStatus
from src.services.stock_analysis_service import StockAnalysisService
from src.services.watchlist_service import WatchlistService
from src.ui.components.page_scaffold import (
    render_empty_state,
    render_kpi_row,
    render_page_header,
    safe_service_call,
    summarize_filters,
)
from src.ui.components.tables import render_watchlist_status_table


def _render_stock_detail_navigation() -> None:
    with st.form("watchlist_open_detail_form", border=True):
        st.markdown("#### Aktienanalyse öffnen")
        detail_symbol = st.text_input(
            "Symbol für Detailanalyse",
            value=str(st.session_state.get("selected_stock_symbol") or ""),
            placeholder="z. B. AAPL",
        )
        open_detail = st.form_submit_button("Analyse öffnen", type="primary")
        if open_detail:
            normalized_detail_symbol = str(detail_symbol or "").strip().upper()
            if normalized_detail_symbol:
                st.session_state["selected_stock_symbol"] = normalized_detail_symbol
                st.session_state["nav_target"] = "Stock-Detail"
                st.rerun()
            else:
                st.warning("Bitte ein Symbol für die Detailanalyse eingeben.")


def _normalize_watchlist_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for column in [
        "symbol",
        "display_name",
        "notes",
        "resolution_status",
        "profile_status_text",
        "price_status_text",
        "financial_status_text",
        "prediction_status_text",
        "preference_status_text",
        "data_quality_summary",
    ]:
        if column not in df.columns:
            df[column] = None
    df["symbol"] = df["symbol"].astype(str).str.upper()
    df["display_name"] = df["display_name"].fillna("—")
    df["notes"] = df["notes"].fillna("—")
    df["resolution_status"] = df["resolution_status"].fillna("UNRESOLVED").astype(str).str.upper()
    df["profile_status_text"] = df["profile_status_text"].fillna("—")
    df["price_status_text"] = df["price_status_text"].fillna("—")
    df["financial_status_text"] = df["financial_status_text"].fillna("—")
    df["prediction_status_text"] = df["prediction_status_text"].fillna("—")
    df["preference_status_text"] = df["preference_status_text"].fillna("—")
    df["data_quality_summary"] = df["data_quality_summary"].fillna("—")
    return df


def render_watchlist_page(
    watchlist_service: WatchlistService | None,
    analysis_service: StockAnalysisService | None = None,
    db_status: DatabaseStatus | None = None,
) -> None:
    """Rendert die manuelle Watchlist mit sichtbar textuellen Statuswerten."""

    render_page_header(
        "Watchlist",
        "Manuell gepflegte Aktienliste mit sichtbaren Statuswerten fuer Profil, Kurse, Finanzdaten und Rankings.",
    )
    _render_stock_detail_navigation()
    if watchlist_service is None:
        st.warning("Watchlist ist derzeit nicht verfuegbar, da die MySQL-Repositories fehlen.")
        return

    if analysis_service is None:
        analysis_service = StockAnalysisService(watchlist_service.repository, None)

    feedback = st.session_state.pop("watchlist_feedback", None)
    feedback_kind = str(st.session_state.pop("watchlist_feedback_kind", "success") or "success")
    if feedback:
        if feedback_kind == "error":
            st.error(str(feedback))
        else:
            st.success(str(feedback))

    summary, summary_error = safe_service_call(
        lambda: analysis_service.build_watchlist_summary(active_only=False),
        context_label="Watchlist-Zusammenfassung",
        fallback={"total_items": 0, "active_items": 0, "resolved_items": 0, "unresolved_items": 0, "unresolved_text": ""},
    )
    if summary_error is not None:
        st.warning("Watchlist-Zusammenfassung konnte nicht geladen werden.")

    render_kpi_row(
        [
            {"label": "Eintraege", "value": str(summary["total_items"])},
            {"label": "Aktiv", "value": str(summary["active_items"])},
            {"label": "Unaufgeloest", "value": str(summary["unresolved_items"]), "subtext": summary["unresolved_text"]},
            {"label": "Aufgeloest", "value": str(summary["resolved_items"])},
        ]
    )

    summarize_filters(
        "Watchlist-Status",
        {
            "Datenbank": db_status.mysql.is_connected if db_status else "unbekannt",
            "Analyse": db_status.is_analysis_available if db_status else "unbekannt",
        },
    )

    with st.expander("Watchlist-Eintrag speichern oder bearbeiten", expanded=True):
        current_rows = analysis_service.list_watchlist_items_with_status(active_only=False)
        current_symbols = ["(neu)"] + [str(row.get("symbol") or "").strip().upper() for row in current_rows]
        selected_symbol = st.selectbox(
            "Eintrag",
            options=current_symbols,
            key="watchlist_selected_symbol",
        )
        current_item = None
        if selected_symbol != "(neu)":
            current_item = watchlist_service.get_item(selected_symbol)

        default_symbol = str(current_item.get("symbol") if current_item else "").strip().upper()
        default_display_name = str(current_item.get("display_name") if current_item and current_item.get("display_name") else "")
        default_notes = str(current_item.get("notes") if current_item and current_item.get("notes") else "")
        default_priority = int(current_item.get("priority") or 0) if current_item else 0
        default_active = bool(current_item.get("active", True)) if current_item else True
        default_resolution_status = str(current_item.get("resolution_status") or "UNRESOLVED").upper() if current_item else "UNRESOLVED"

        form_suffix = selected_symbol.replace(" ", "_").replace("(", "").replace(")", "")
        with st.form(f"watchlist_edit_form_{form_suffix}"):
            symbol = st.text_input("Symbol", value=default_symbol, key=f"watchlist_symbol_input_{form_suffix}")
            display_name = st.text_input("Name", value=default_display_name, key=f"watchlist_display_name_input_{form_suffix}")
            notes = st.text_area("Notizen", value=default_notes, key=f"watchlist_notes_input_{form_suffix}")
            priority = st.number_input("Prioritaet", min_value=0, max_value=100, step=1, value=default_priority, key=f"watchlist_priority_input_{form_suffix}")
            active = st.checkbox("Aktiv", value=default_active, key=f"watchlist_active_input_{form_suffix}")
            resolution_status = st.text_input(
                "Resolution-Status",
                value=default_resolution_status,
                key=f"watchlist_resolution_status_input_{form_suffix}",
                help="Status bleibt sichtbar, auch wenn der Symbol-Match noch nicht abgeschlossen ist.",
            )
            submitted = st.form_submit_button("Speichern", type="primary")
            if submitted:
                try:
                    watchlist_service.upsert_item(
                        symbol,
                        display_name=display_name,
                        notes=notes,
                        priority=int(priority),
                        active=bool(active),
                        resolution_status=resolution_status,
                    )
                except Exception as exc:  # noqa: BLE001 - UI-Schutz
                    st.session_state["watchlist_feedback"] = f"Watchlist-Eintrag konnte nicht gespeichert werden: {exc}"
                    st.session_state["watchlist_feedback_kind"] = "error"
                else:
                    st.session_state["watchlist_feedback"] = f"Watchlist-Eintrag {symbol.strip().upper()} gespeichert."
                    st.session_state["watchlist_feedback_kind"] = "success"
                st.rerun()

        if selected_symbol != "(neu)" and st.button("Eintrag entfernen", key=f"watchlist_delete_{form_suffix}", use_container_width=True):
            try:
                watchlist_service.delete_item(selected_symbol)
            except Exception as exc:  # noqa: BLE001 - UI-Schutz
                st.session_state["watchlist_feedback"] = f"Watchlist-Eintrag konnte nicht geloescht werden: {exc}"
                st.session_state["watchlist_feedback_kind"] = "error"
            else:
                st.session_state["watchlist_feedback"] = f"Watchlist-Eintrag {selected_symbol} geloescht."
                st.session_state["watchlist_feedback_kind"] = "success"
            st.rerun()

    rows = current_rows
    if not rows:
        render_empty_state("Noch keine Watchlist-Eintraege vorhanden.")
        return

    df = _normalize_watchlist_df(rows)
    st.subheader("Watchlist-Status")
    st.caption(
        "Alle Eintraege bleiben sichtbar. Profil-, Kurs-, Finanz-, Prognose- und Preference-Status erscheinen als Text, "
        "auch wenn die entsprechenden Analysedaten noch nicht importiert sind."
    )
    render_watchlist_status_table(df)
