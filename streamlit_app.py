"""Einstiegspunkt der Streamlit-Anwendung Mercator."""

from __future__ import annotations

import streamlit as st

from src.config.settings import AppSettings, load_settings
from src.data_sources.fmp_client import FmpClient
from src.db.mongo_client import MongoClientWrapper
from src.db.mongo_repository import CompanyMongoRepository, InsiderTradeMongoRepository
from src.db.mysql_client_factory import build_mysql_client_for_target
from src.db.mysql_repository import CompanyMySqlRepository, InsiderTradeMySqlRepository
from src.db.mysql_target_resolver import MySqlResolutionResult
from src.services.analysis_service import AnalysisService
from src.services.database_status_service import DatabaseStatusService
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService
from src.services.mysql_sync_service import MySqlSyncService
from src.preprocessing import GateEvaluator, GateRules
from src.ui.pages.dashboard_page import render_dashboard_page
from src.ui.pages.explorer_page import render_explorer_page
from src.ui.pages.methodology_page import render_methodology_page
from src.ui.pages.ticker_detail_page import render_ticker_detail_page

MYSQL_TARGET_STATE_KEY = "mysql_runtime_target"


def _render_database_sidebar_status(status_service: DatabaseStatusService, settings: AppSettings) -> MySqlResolutionResult | None:
    """Rendert Sidebar-Steuerung und Status für Datenbanken getrennt."""

    configured_target = settings.mysql.mysql_active_target
    selected_target = st.sidebar.radio(
        "Aktives MySQL-Ziel",
        options=["local", "uni"],
        index=0 if st.session_state.get(MYSQL_TARGET_STATE_KEY, configured_target) == "local" else 1,
        key=MYSQL_TARGET_STATE_KEY,
        horizontal=True,
    )

    status, mysql_resolution = status_service.evaluate(
        mysql_settings=settings.mysql,
        mongo_client=MongoClientWrapper(settings.mongo),
        requested_target=selected_target,
    )

    st.sidebar.markdown("### Datenbankstatus")
    if status.mysql.is_connected and status.mysql.active_target is not None:
        mysql_text = f"MySQL: verbunden mit `{status.mysql.active_target}`"
        if status.mysql.used_fallback:
            mysql_text += " (Fallback aktiv)"
        st.sidebar.success(mysql_text)
    else:
        st.sidebar.error(f"MySQL: aktive Verbindung fehlgeschlagen (`{status.mysql.requested_target}`).")

    for message in status.mysql.messages:
        st.sidebar.caption(message)

    if status.mongo.is_connected:
        st.sidebar.success("MongoDB: verbunden")
    else:
        st.sidebar.warning("MongoDB: nicht erreichbar, Rohdatenspeicherung eingeschränkt.")
        st.sidebar.caption(status.mongo.message)

    return mysql_resolution


def _build_services(
    settings: AppSettings, mysql_resolution: MySqlResolutionResult
) -> tuple[DashboardService, AnalysisService, ImportService | None]:
    """Initialisiert Repositories und Services für die UI."""
    mongo_client = MongoClientWrapper(settings.mongo)
    mysql_client = mysql_resolution.client
    mysql_client.initialize_schema()

    raw_repo: InsiderTradeMongoRepository | None = None
    company_mongo_repo: CompanyMongoRepository | None = None
    try:
        raw_repo = InsiderTradeMongoRepository(mongo_client)
        company_mongo_repo = CompanyMongoRepository(mongo_client)
    except Exception:
        raw_repo = None
        company_mongo_repo = None

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
        fmp_client = FmpClient(settings.fmp)
        if raw_repo is not None and company_mongo_repo is not None:
            import_service = ImportService(
                fmp_client=fmp_client,
                gate_evaluator=gate_evaluator,
                raw_repo=raw_repo,
                company_mongo_repo=company_mongo_repo,
                trade_mysql_repo=trade_repo,
                company_mysql_repo=company_repo,
                profile_fetch_statuses=settings.fmp.profile_gate_filter_statuses,
            )
        else:
            st.session_state["import_service_error"] = (
                "MongoDB ist nicht erreichbar. Import wurde in diesem Lauf deaktiviert."
            )
    except Exception as exc:
        st.session_state["import_service_error"] = str(exc)
        import_service = None
    else:
        if import_service is not None:
            st.session_state.pop("import_service_error", None)

    return (
        DashboardService(raw_repo, company_mongo_repo, trade_repo, company_repo),
        AnalysisService(trade_repo, company_repo),
        import_service,
    )


def _render_sync_controls(settings: AppSettings, mysql_resolution: MySqlResolutionResult | None) -> None:
    """Rendert den kontrollierten Sync-Button für local -> uni."""

    if not settings.mysql.mysql_sync_enabled:
        st.sidebar.info("MySQL-Sync ist per Konfiguration deaktiviert.")
        return

    if mysql_resolution is None:
        st.sidebar.warning("Sync nicht verfügbar: kein aktives MySQL-Ziel erreichbar.")
        return

    if mysql_resolution.active_target != "uni":
        st.sidebar.info("Sync-Button ist nur aktiv, wenn das Ziel `uni` erreichbar ist.")
        return

    st.sidebar.markdown("### MySQL-Sync")
    st.sidebar.caption("Richtung: `local -> uni` (explizit per Klick).")
    if st.sidebar.button("Lokale Daten zur Uni-DB synchronisieren", type="primary"):
        try:
            source_client = build_mysql_client_for_target(settings.mysql, "local")
            target_client = build_mysql_client_for_target(settings.mysql, "uni")
            source_ok, source_message = source_client.test_connection()
            target_ok, target_message = target_client.test_connection()
            if not source_ok or not target_ok:
                st.sidebar.error("Sync abgebrochen: Quell- oder Zielverbindung fehlgeschlagen.")
                st.sidebar.caption(source_message)
                st.sidebar.caption(target_message)
                return

            summary = MySqlSyncService().sync_all(source_client=source_client, target_client=target_client)
            st.sidebar.success("Sync erfolgreich abgeschlossen.")
            st.sidebar.write(
                f"Companies: gelesen={summary.company_result.read_count}, "
                f"geschrieben={summary.company_result.written_count}, "
                f"übersprungen={summary.company_result.skipped_count}"
            )
            st.sidebar.write(
                f"Insider-Trades: gelesen={summary.insider_trade_result.read_count}, "
                f"geschrieben={summary.insider_trade_result.written_count}, "
                f"übersprungen={summary.insider_trade_result.skipped_count}"
            )
        except Exception as exc:
            st.sidebar.error(f"Sync fehlgeschlagen: {exc}")


def main() -> None:
    """Konfiguriert Navigation und rendert die gewählte Seite."""
    st.set_page_config(page_title="FinanzPort Academic", layout="wide")
    st.sidebar.title("FinanzPort Academic")
    st.sidebar.caption("Interaktive Datenanwendung für das Modul Datenbanken 2")

    settings = load_settings()
    status_service = DatabaseStatusService()
    mysql_resolution = _render_database_sidebar_status(status_service, settings)
    _render_sync_controls(settings, mysql_resolution)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### App-Konfiguration")
    advanced_mode = st.sidebar.toggle("Erweiterte Ansicht (Advanced Mode)", value=False)
    st.session_state["advanced_mode"] = advanced_mode

    if mysql_resolution is None:
        st.error("MySQL: aktive Datenbank nicht erreichbar. Bitte Einstellungen prüfen.")
        render_methodology_page()
        return

    try:
        dashboard_service, analysis_service, import_service = _build_services(settings, mysql_resolution)
    except Exception as exc:
        st.sidebar.error(f"MySQL-Initialisierung fehlgeschlagen: {exc}")
        render_methodology_page()
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
