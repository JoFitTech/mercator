"""Unternehmens-Detailseite (Requirement 7)."""

from __future__ import annotations
from typing import Any
import streamlit as st
import pandas as pd
from src.services.analysis_service import AnalysisService
from src.services.database_status_service import DatabaseStatus
from src.services.import_service import ImportService
from src.ui.components.formatting import (
    _is_incomplete_profile,
    _normalize_profile_status,
    _normalize_website_url,
    _profile_status_label,
    _ui_text,
)
from src.ui.components.page_scaffold import render_page_header, render_empty_state, render_kpi_row
from src.ui.components.tables import get_single_selected_row_index, render_trade_table


def _safe_text(value: object, fallback: str = "—") -> str:
    """Kompatibilitäts-Wrapper für bestehende Tests/Altaufrufe."""
    return _ui_text(value, fallback=fallback)


def _format_market_cap(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _refresh_capability(import_service: ImportService | None) -> tuple[bool, str | None]:
    if import_service is None:
        return False, "Profil-Refresh-Service ist nicht verfügbar."
    if not callable(getattr(import_service, "refresh_company_profile_for_symbol", None)):
        return False, "Profil-Refresh-Service ist nicht verfügbar."
    return True, None


def _refresh_company_profile(import_service: ImportService, symbol: str) -> dict[str, Any]:
    result = import_service.refresh_company_profile_for_symbol(symbol)
    if isinstance(result, dict):
        return result
    return {"ok": False, "message": "Unerwartete Antwort vom Profil-Refresh-Service."}


def render_company_detail_page(
    service: AnalysisService | None,
    symbol: str | None = None,
    db_status: DatabaseStatus | None = None,
    import_service: ImportService | None = None,
) -> None:
    """Rendert die Detailseite für ein Unternehmen."""
    if service is None:
        render_empty_state("Unternehmensdetails sind derzeit nicht verfügbar, da die Analyse-Datenbank offline ist.")
        return

    if not symbol:
        symbol = st.session_state.get("selected_company_symbol")

    symbol = str(symbol or "").strip() if symbol else None

    if not symbol:
        render_empty_state("Kein Unternehmen ausgewählt.")
        if st.button("Zurück zur Unternehmensübersicht"):
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
    company_name = _ui_text(profile.get("company_name"), fallback=symbol)
    sector = _ui_text(profile.get("sector"), fallback="Sektor offen")
    industry = _ui_text(profile.get("industry"), fallback="Industrie offen")
    country = _ui_text(profile.get("country"), fallback="Land offen")
    profile_status_raw = _normalize_profile_status(profile.get("profile_status"))
    profile_status_label = _profile_status_label(profile.get("profile_status"))
    profile_incomplete = _is_incomplete_profile(profile)

    render_page_header(
        f"{symbol} - {company_name}",
        f"{sector} | {industry} | {country}"
    )

    can_refresh, refresh_block_reason = _refresh_capability(import_service)
    refresh_disabled = (not bool(symbol)) or (not can_refresh)
    refresh_btn_label = (
        "Profil erneut per API2 aktualisieren" if not profile_incomplete
        else "Profil per API2 aktualisieren"
    )
    if st.button(
        refresh_btn_label,
        use_container_width=False,
        disabled=refresh_disabled,
        help=(refresh_block_reason or "") if refresh_disabled else None,
        key=f"company_detail_refresh_{symbol}",
    ):
        with st.spinner("Lade Unternehmensprofil über API2 nach..."):
            result_refresh = _refresh_company_profile(import_service, symbol)  # type: ignore[arg-type]
        if bool(result_refresh.get("ok")):
            st.success(f"Profil für {symbol} wurde aktualisiert.")
        else:
            st.error(str(result_refresh.get("message") or "Profilaktualisierung fehlgeschlagen."))
        st.rerun()
    if refresh_block_reason and not can_refresh:
        st.caption(refresh_block_reason)
    if profile_incomplete:
        st.warning("Profilinformationen sind unvollständig. Sie können das Profil per API2 nachladen.")

    # 1. KPIs (Requirement 7.2)
    metrics = result.metrics or {}
    kpis = [
        {"label": "Marktkapitalisierung", "value": _format_market_cap(profile.get("market_cap"))},
        {"label": "Anzahl Trades", "value": str(metrics.get("trade_count", 0))},
        {"label": "Durchschn. Score", "value": f"{metrics.get('overall_score', 0):.1f}"},
        {"label": "Profilstatus", "value": profile_status_label},
    ]
    render_kpi_row(kpis)

    # 2. Profil-Sektion
    description = _ui_text(
        profile.get("description"),
        fallback="Keine Unternehmensbeschreibung aus API2 verfügbar.",
    )
    website_url = _normalize_website_url(profile.get("website"))
    with st.expander("Unternehmensprofil & Beschreibung", expanded=description != "Keine Unternehmensbeschreibung aus API2 verfügbar."):
        st.write(description)
        if website_url:
            st.link_button("Website besuchen", website_url)
        with st.expander("Technischer Profilstatus", expanded=False):
            st.write(_ui_text(profile_status_raw, fallback="—"))

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
