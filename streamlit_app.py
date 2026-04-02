"""Zentraler Streamlit-Einstiegspunkt für Mercator."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config.settings import load_settings
from src.services.analysis_service import AnalysisService
from src.services.dashboard_service import DashboardService
from src.ui.pages.dashboard_page import render_dashboard_page
from src.ui.pages.explorer_page import render_explorer_page
from src.ui.pages.methodology_page import render_methodology_page
from src.ui.pages.ticker_detail_page import render_ticker_detail_page


def _load_demo_dataframe() -> pd.DataFrame:
    """Lädt optional lokale Demodaten.

    Hinweis:
        Aktuell wird kein fester Datensatz vorausgesetzt. Falls in `data/processed`
        eine `trades_clean.csv` liegt, wird diese für UI-Demos verwendet.
    """
    try:
        return pd.read_csv("data/processed/trades_clean.csv")
    except FileNotFoundError:
        return pd.DataFrame()


def main() -> None:
    """Initialisiert Navigation und rendert die ausgewählte Seite."""
    settings = load_settings()
    analysis_service = AnalysisService()
    dashboard_service = DashboardService(analysis_service)

    st.set_page_config(page_title=settings.app_title, layout="wide")
    st.sidebar.title(settings.app_title)
    st.sidebar.caption("Interaktive Datenanwendung für das Modul Datenbanken 2")

    page = st.sidebar.radio(
        "Navigation",
        options=["Dashboard", "Datenexplorer", "Ticker-Detailansicht", "Methodik und Datenfluss"],
    )

    trades_df = _load_demo_dataframe()

    # DB-Fehlerhinweis wird angezeigt, solange noch keine Daten in den Zieldateien liegen.
    if trades_df.empty:
        st.sidebar.warning(
            "Die Datenbankverbindung konnte nicht aufgebaut werden. Prüfe die Umgebungsvariablen in der .env-Datei und die Erreichbarkeit von MySQL bzw. MongoDB."
        )

    if page == "Dashboard":
        render_dashboard_page(dashboard_service, trades_df)
    elif page == "Datenexplorer":
        render_explorer_page(trades_df)
    elif page == "Ticker-Detailansicht":
        render_ticker_detail_page(trades_df)
    else:
        render_methodology_page()


if __name__ == "__main__":
    main()
