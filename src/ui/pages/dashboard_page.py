"""Dashboard-Seite mit KPIs und Basisvisualisierungen."""

from __future__ import annotations

import streamlit as st

from src.config.settings import AppSettings
from src.preprocessing.gate_evaluator import (
    GATE_FAIL,
    GATE_PASS,
    GATE_PENDING,
    GATE_PROFILE_FETCHED,
    GATE_PROFILE_FETCH_FAILED,
)
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService


EMPTY_DATA_MESSAGE = (
    "Es sind aktuell noch keine verarbeiteten Daten verfügbar. "
    "Lade zunächst einen Datensatz oder prüfe die Datenbankverbindung."
)


def render_dashboard_page(
    service: DashboardService,
    import_service: ImportService | None = None,
    settings: AppSettings | None = None,
) -> None:
    """Rendert KPI-Karten und Diagramme für den Gesamtüberblick."""
    st.title("FinanzPort Academic")
    st.markdown("### Dashboard")
    st.caption("Überblick über importierte Datensätze, Kennzahlen und erste Analyseergebnisse.")

    advanced_mode = st.session_state.get("advanced_mode", False)

    if settings is not None:
        with st.expander("Import-Steuerung & Konfiguration", expanded=advanced_mode):
            st.subheader("FMP API Import")
            c1, c2 = st.columns(2)
            page = c1.number_input(
                "Feed-Seite (Standard: 0)", min_value=0, step=1, value=settings.fmp.default_feed_page
            )
            limit = c2.number_input(
                "Feed-Limit (Standard: 100)", min_value=1, max_value=1000, step=10, value=settings.fmp.default_feed_limit
            )

            status_options = [
                GATE_PASS,
                GATE_PENDING,
                GATE_FAIL,
                GATE_PROFILE_FETCHED,
                GATE_PROFILE_FETCH_FAILED,
            ]
            selected_statuses = st.multiselect(
                "Gate-Status für Profil-Anreicherung (API 2)",
                options=status_options,
                default=list(settings.fmp.profile_gate_filter_statuses),
                help="Profil-Abfrage erfolgt nur für Trades mit diesen Statuswerten.",
            )

            if advanced_mode:
                st.info(
                    "Gate-Regeln (Read-only): min_trade_value=%s, require_purchase=%s, require_common_stock=%s"
                    % (
                        settings.gate.min_trade_value,
                        settings.gate.require_purchase_event,
                        settings.gate.require_common_stock,
                    )
                )

            if st.button("Datenimport jetzt starten", type="primary", use_container_width=True):
                if import_service is None:
                    st.error("ImportService ist nicht aktiv. Bitte FMP_API_KEY in .env prüfen.")
                    error_detail = st.session_state.get("import_service_error")
                    if error_detail:
                        st.caption(f"Technischer Hinweis: {error_detail}")
                else:
                    with st.spinner("Import läuft..."):
                        summary = import_service.run_hourly_import(
                            page=int(page),
                            limit=int(limit),
                            profile_fetch_statuses=tuple(selected_statuses),
                        )
                    st.success(
                        "Import erfolgreich abgeschlossen: %s Rohdatensätze, %s Profile geladen."
                        % (summary.fetched_feed_records, summary.fetched_profiles)
                    )

    payload = service.build_dashboard_payload()

    if payload["clean_records"] == 0:
        st.warning(EMPTY_DATA_MESSAGE)
        return

    st.markdown("---")
    st.subheader("Zentrale Kennzahlen")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rohdaten (Mongo)", f"{payload['raw_records']:,}")
    c2.metric("Bereinigte Trades (MySQL)", f"{payload['clean_records']:,}")
    c3.metric("Unternehmensprofile", f"{payload['company_profiles']:,}")
    
    # Optional: Ein fiktiver Score oder eine zusätzliche Kennzahl
    pass_count = payload.get("gate_pass_records", 0)
    c4.metric("Gate-PASS", f"{pass_count:,}")

    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Transaktionstypen")
        st.bar_chart(payload["transaction_type_distribution"].set_index("transaction_type"))

    with col_right:
        st.subheader("Sektoren-Verteilung")
        st.bar_chart(payload["sector_distribution"].set_index("sector"))

    if advanced_mode:
        st.markdown("---")
        st.subheader("Zeitliche Verteilung (Filing Date)")
        st.line_chart(payload["timeline_distribution"].set_index("event_date"))
