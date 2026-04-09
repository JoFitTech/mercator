"""Einstiegspunkt der Streamlit-Anwendung Mercator."""

from __future__ import annotations

from dataclasses import replace

import streamlit as st

from src.config.settings import AppSettings, load_settings
from src.data_sources.fmp_client import FmpClient
from src.db.mongo_client import MongoClientWrapper
from src.db.mongo_repository import AppSettingsMongoRepository, CompanyMongoRepository, InsiderTradeMongoRepository
from src.db.mysql_client_factory import build_mysql_client_for_target
from src.db.mysql_repository import CompanyMySqlRepository, InsiderTradeMySqlRepository
from src.db.mysql_target_resolver import MySqlResolutionResult
from src.services.analysis_service import AnalysisService
from src.services.database_status_service import DatabaseStatusService
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService
from src.services.app_settings_service import AppSettingsService
from src.services.mysql_sync_service import MySqlSyncService
from src.services.factory import ServiceFactory
from src.preprocessing import GateEvaluator, GateRules
from src.ui.pages.dashboard_page import render_dashboard_page
from src.ui.pages.explorer_page import render_explorer_page
from src.ui.pages.methodology_page import render_methodology_page
from src.ui.pages.ticker_detail_page import render_ticker_detail_page

MYSQL_TARGET_STATE_KEY = "mysql_runtime_target"


def _render_database_sidebar_status(
    status_service: DatabaseStatusService, settings: AppSettings, advanced_mode: bool = False
) -> MySqlResolutionResult | None:
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

    with st.sidebar.expander("Datenbank-Status", expanded=advanced_mode):
        if status.mysql.is_connected and status.mysql.active_target is not None:
            mysql_text = f"MySQL: verbunden mit `{status.mysql.active_target}`"
            if status.mysql.used_fallback:
                mysql_text += " (Fallback aktiv)"
            st.success(mysql_text)
        else:
            st.error(f"MySQL: aktive Verbindung fehlgeschlagen (`{status.mysql.requested_target}`).")

        for message in status.mysql.messages:
            st.caption(message)

        if status.mongo.is_connected:
            st.success("MongoDB: verbunden")
        else:
            st.warning("MongoDB: nicht erreichbar, Rohdatenspeicherung eingeschränkt.")
            st.caption(status.mongo.message)

    return mysql_resolution


def _build_services(
    settings: AppSettings, mysql_resolution: MySqlResolutionResult
) -> tuple[DashboardService, AnalysisService, ImportService | None, AppSettingsService]:
    """Initialisiert Repositories und Services für die UI."""
    try:
        return ServiceFactory.build_all(settings, mysql_resolution.client)
    except Exception as exc:
        st.session_state["import_service_error"] = f"Fehler bei Service-Initialisierung: {exc}"
        # Fallback-Build ohne MongoDB-Abhängigkeit falls möglich oder einfach Re-raise
        raise exc


def _render_sync_controls(settings: AppSettings, mysql_resolution: MySqlResolutionResult | None) -> None:
    """Rendert den kontrollierten Sync-Button für local <-> uni."""

    if not settings.mysql.mysql_sync_enabled:
        st.sidebar.info("MySQL-Sync ist per Konfiguration deaktiviert.")
        return

    if mysql_resolution is None:
        st.sidebar.warning("Sync nicht verfügbar: kein aktives MySQL-Ziel erreichbar.")
        return

    st.sidebar.markdown("### MySQL-Sync (Bidirektional)")

    direction = st.sidebar.radio(
        "Sync-Richtung",
        options=["auto", "local -> uni", "uni -> local"],
        index=0,
        help="Wählt aus, in welche Richtung die Daten abgeglichen werden sollen. 'auto' nutzt den neuesten Zeitstempel.",
    )

    dir_map = {
        "auto": "auto",
        "local -> uni": "local_to_uni",
        "uni -> local": "uni_to_local",
    }

    if st.sidebar.button("Synchronisierung jetzt starten", type="primary"):
        try:
            local_client = build_mysql_client_for_target(settings.mysql, "local")
            uni_client = build_mysql_client_for_target(settings.mysql, "uni")

            # Beides muss erreichbar sein fuer Sync
            local_ok, local_msg = local_client.test_connection()
            uni_ok, uni_msg = uni_client.test_connection()

            if not local_ok or not uni_ok:
                st.sidebar.error("Sync abgebrochen: Beide Datenbanken müssen erreichbar sein.")
                if not local_ok:
                    st.sidebar.caption(f"Lokal: {local_msg}")
                if not uni_ok:
                    st.sidebar.caption(f"Uni: {uni_msg}")
                return

            with st.spinner("Synchronisiere Daten..."):
                summary = MySqlSyncService().sync_all(
                    local_client=local_client,
                    uni_client=uni_client,
                    direction=dir_map[direction],
                )

            st.sidebar.success(f"Sync ({summary.direction}) abgeschlossen.")
            st.sidebar.write(f"**Companies:** {summary.company_result.written_count} aktualisiert")
            st.sidebar.write(f"**Trades:** {summary.insider_trade_result.written_count} aktualisiert")

            if summary.company_result.written_count > 0 or summary.insider_trade_result.written_count > 0:
                st.toast("Daten wurden erfolgreich synchronisiert!", icon="🔄")
                st.rerun()

        except Exception as exc:
            st.sidebar.error(f"Sync fehlgeschlagen: {exc}")


def main() -> None:
    """Konfiguriert Navigation und rendert die gewählte Seite."""
    st.set_page_config(page_title="Mercator", layout="wide")
    st.sidebar.title("Mercator")
    st.sidebar.caption("Interaktive Datenanwendung für das Modul Datenbanken 2")

    st.sidebar.markdown("### App-Konfiguration")
    advanced_mode = st.sidebar.toggle("Erweiterte Ansicht (Advanced Mode)", value=False)
    st.session_state["advanced_mode"] = advanced_mode
    st.sidebar.markdown("---")

    settings = load_settings()
    status_service = DatabaseStatusService()
    mysql_resolution = _render_database_sidebar_status(status_service, settings, advanced_mode)
    
    if advanced_mode:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### DB-Doctor")
        if st.sidebar.button("Schema-Check & Reparatur (Alle Ziele)", help="Analysiert und repariert das Schema auf local und uni."):
            try:
                from src.scripts.init_mysql_schema import initialize_all_targets
                with st.spinner("DB-Doctor analysiert..."):
                    results = initialize_all_targets()
                
                for target, actions in results.items():
                    if not actions:
                        st.sidebar.success(f"{target}: Aktuell")
                    elif any(a.startswith("FAILED") for a in actions):
                        st.sidebar.error(f"{target}: Fehlerhaft")
                        for a in actions: st.sidebar.caption(a)
                    else:
                        st.sidebar.warning(f"{target}: {len(actions)} Fixes")
                        with st.sidebar.expander(f"Details {target}"):
                            for a in actions: st.sidebar.write(f"- {a}")
            except Exception as e:
                st.sidebar.error(f"Doctor-Lauf fehlgeschlagen: {e}")

    _render_sync_controls(settings, mysql_resolution)

    if mysql_resolution is None:
        st.error("MySQL: aktive Datenbank nicht erreichbar. Bitte Einstellungen prüfen.")
        render_methodology_page()
        return

    try:
        dashboard_service, analysis_service, import_service, runtime_settings_service = _build_services(settings, mysql_resolution)
    except Exception as exc:
        st.sidebar.error(f"MySQL-Initialisierung fehlgeschlagen: {exc}")
        render_methodology_page()
        return

    def _dashboard() -> None:
        render_dashboard_page(dashboard_service, import_service, settings, runtime_settings_service)

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
