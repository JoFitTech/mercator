"""Einstiegspunkt der Streamlit-Anwendung Mercator."""

from __future__ import annotations

import streamlit as st

from src.config.settings import AppSettings, load_settings
from src.data_sources.fmp_api_client import FmpApiClient
from src.db.mongo_client import MongoClientWrapper
from src.db.mongo_repository import CompanyMongoRepository, InsiderTradeMongoRepository
from src.db.mysql_client import MySqlClient
from src.db.mysql_repository import CompanyMySqlRepository, InsiderTradeMySqlRepository
from src.services.analysis_service import AnalysisService
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService
from src.preprocessing import GateEvaluator, GateRules
from src.ui.pages.dashboard_page import render_dashboard_page
from src.ui.pages.explorer_page import render_explorer_page
from src.ui.pages.methodology_page import render_methodology_page
from src.ui.pages.ticker_detail_page import render_ticker_detail_page

DB_ERROR_MESSAGE = (
    "Die Datenbankverbindung konnte nicht aufgebaut werden. "
    "Prüfe die Umgebungsvariablen in der .env-Datei und die Erreichbarkeit von MySQL bzw. MongoDB."
)


def _build_services() -> tuple[DashboardService, AnalysisService, ImportService | None, AppSettings]:
    """Initialisiert Repositories und Services für die UI."""
    settings = load_settings()
    mongo_client = MongoClientWrapper(settings.mongo)
    mysql_client = MySqlClient(settings.mysql)
    mysql_client.initialize_schema()

    raw_repo = InsiderTradeMongoRepository(mongo_client)
    company_mongo_repo = CompanyMongoRepository(mongo_client)
    trade_repo = InsiderTradeMySqlRepository(mysql_client)
    company_repo = CompanyMySqlRepository(mysql_client)

    import_service: ImportService | None = None
    try:
        gate_evaluator = GateEvaluator(
            GateRules(
                min_trade_value=settings.gate.min_trade_value,
                require_purchase_event=settings.gate.require_purchase_event,
                require_common_stock=settings.gate.require_common_stock,
            )
        )
        fmp_client = FmpApiClient(settings.fmp)
        import_service = ImportService(
            fmp_client=fmp_client,
            gate_evaluator=gate_evaluator,
            raw_repo=raw_repo,
            company_mongo_repo=company_mongo_repo,
            trade_mysql_repo=trade_repo,
            company_mysql_repo=company_repo,
            profile_fetch_statuses=settings.fmp.profile_gate_filter_statuses,
        )
    except Exception as exc:
        st.session_state["import_service_error"] = str(exc)
        import_service = None
    else:
        st.session_state.pop("import_service_error", None)

    return (
        DashboardService(raw_repo, company_mongo_repo, trade_repo, company_repo),
        AnalysisService(trade_repo, company_repo),
        import_service,
        settings,
    )


def main() -> None:
    """Konfiguriert Navigation und rendert die gewählte Seite."""
    st.set_page_config(page_title="Mercator", layout="wide")
    st.sidebar.title("Mercator")
    st.sidebar.caption("Interaktive Datenanwendung für das Modul Datenbanken 2")

    try:
        dashboard_service, analysis_service, import_service, settings = _build_services()
    except Exception:
        st.sidebar.error(DB_ERROR_MESSAGE)

        def _methodology_only() -> None:
            render_methodology_page()

        nav = st.navigation(
            [
                st.Page(_methodology_only, title="Methodik", icon=":material/schema:", default=True),
            ]
        )
        nav.run()
        st.warning(DB_ERROR_MESSAGE)
        return

    def _dashboard() -> None:
        render_dashboard_page(dashboard_service, import_service, settings)

    def _explorer() -> None:
        render_explorer_page(analysis_service)

    def _ticker_detail() -> None:
        render_ticker_detail_page(analysis_service)

    pages = [
        st.Page(_dashboard, title="Dashboard", icon=":material/dashboard:", default=True),
        st.Page(_explorer, title="Explorer", icon=":material/table_view:"),
        st.Page(_ticker_detail, title="Ticker-Detailansicht", icon=":material/insights:"),
        st.Page(render_methodology_page, title="Methodik", icon=":material/schema:"),
    ]
    nav = st.navigation(pages)
    nav.run()


if __name__ == "__main__":
    main()
