"""Dashboard-Seite für Mercator."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.services.dashboard_service import DashboardService


def render_dashboard_page(dashboard_service: DashboardService, trades_df: pd.DataFrame) -> None:
    """Rendert KPI-Überblick und Einordnung für die Startseite."""
    st.title("Dashboard")
    st.caption("Überblick über importierte Datensätze, Kennzahlen und erste Analyseergebnisse.")

    payload = dashboard_service.build_dashboard_payload(trades_df)

    if payload["row_count"] == 0:
        st.warning(
            "Es sind aktuell noch keine verarbeiteten Daten verfügbar. Lade zunächst einen Datensatz oder prüfe die Datenbankverbindung."
        )
        return

    c1, c2 = st.columns(2)
    c1.metric("Datensätze", payload["kpis"].get("rows", 0))
    c2.metric("Eindeutige Ticker", payload["kpis"].get("unique_ticker", 0))
    st.info(payload["note"])
