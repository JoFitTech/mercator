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
    st.title("Dashboard")
    st.caption("Überblick über importierte Datensätze, Kennzahlen und erste Analyseergebnisse.")

    st.subheader("Import- und Gate-Konfiguration")
    if settings is None:
        st.info("Konfiguration konnte nicht geladen werden.")
    else:
        with st.expander("API- und Filtereinstellungen", expanded=False):
            page = st.number_input(
                "Feed-Seite (API 1)", min_value=0, step=1, value=settings.fmp.default_feed_page
            )
            limit = st.number_input(
                "Feed-Limit (API 1)", min_value=1, max_value=1000, step=10, value=settings.fmp.default_feed_limit
            )

            status_options = [
                GATE_PASS,
                GATE_PENDING,
                GATE_FAIL,
                GATE_PROFILE_FETCHED,
                GATE_PROFILE_FETCH_FAILED,
            ]
            selected_statuses = st.multiselect(
                "Gate-Status, die API 2 triggern",
                options=status_options,
                default=list(settings.fmp.profile_gate_filter_statuses),
                help="Code-Default kommt aus PROFILE_GATE_FILTER_STATUSES in .env und kann hier pro Lauf ueberschrieben werden.",
            )

            st.caption(
                "Code-Default: min_trade_value=%s, require_purchase=%s, require_common_stock=%s"
                % (
                    settings.gate.min_trade_value,
                    settings.gate.require_purchase_event,
                    settings.gate.require_common_stock,
                )
            )

            run_import = st.button("Import jetzt starten", type="primary")
            if run_import:
                if import_service is None:
                    st.error("ImportService ist nicht aktiv. Pruefe FMP_API_KEY in .env.")
                    error_detail = st.session_state.get("import_service_error")
                    if error_detail:
                        st.caption(f"Technischer Hinweis: {error_detail}")
                else:
                    summary = import_service.run_hourly_import(
                        page=int(page),
                        limit=int(limit),
                        profile_fetch_statuses=tuple(selected_statuses),
                    )
                    st.success(
                        "Import fertig: feed=%s, raw=%s, clean=%s, profiles=%s"
                        % (
                            summary.fetched_feed_records,
                            summary.inserted_raw_records,
                            summary.upserted_clean_records,
                            summary.fetched_profiles,
                        )
                    )

    payload = service.build_dashboard_payload()

    if payload["clean_records"] == 0:
        st.warning(EMPTY_DATA_MESSAGE)
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Rohdatensätze (MongoDB)", payload["raw_records"])
    c2.metric("Bereinigte Datensätze (MySQL)", payload["clean_records"])
    c3.metric("Firmenprofile", payload["company_profiles"])

    st.subheader("Verteilung nach transaction_type")
    st.bar_chart(payload["transaction_type_distribution"].set_index("transaction_type"))

    st.subheader("Verteilung nach sector")
    st.bar_chart(payload["sector_distribution"].set_index("sector"))

    st.subheader("Zeitliche Verteilung")
    st.line_chart(payload["timeline_distribution"].set_index("event_date"))
