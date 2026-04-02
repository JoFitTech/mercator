"""Dashboard-Seite mit KPIs und Basisvisualisierungen."""

from __future__ import annotations

import streamlit as st

from src.services.dashboard_service import DashboardService


EMPTY_DATA_MESSAGE = (
    "Es sind aktuell noch keine verarbeiteten Daten verfügbar. "
    "Lade zunächst einen Datensatz oder prüfe die Datenbankverbindung."
)


def render_dashboard_page(service: DashboardService) -> None:
    """Rendert KPI-Karten und Diagramme für den Gesamtüberblick."""
    st.title("Dashboard")
    st.caption("Überblick über importierte Datensätze, Kennzahlen und erste Analyseergebnisse.")

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
