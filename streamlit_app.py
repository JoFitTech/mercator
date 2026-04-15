"""Einstiegspunkt der Streamlit-Anwendung Mercator."""

from __future__ import annotations

from typing import Literal


import streamlit as st

from src.config.settings import AppSettings, load_settings
from src.db.mongo_client import MongoClientWrapper
from src.db.mysql_client_factory import build_mysql_client_for_target
from src.db.mysql_target_resolver import MySqlResolutionResult
from src.services.analysis_service import AnalysisService
from src.services.database_status_service import DatabaseStatus, DatabaseStatusService, MongoStatus, MySqlStatus
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService
from src.services.app_settings_service import AppSettingsService
from src.services.mysql_sync_service import MySqlSyncService
from src.services.factory import ServiceFactory
from src.ui.pages.dashboard_page import render_dashboard_page
from src.ui.pages.explorer_page import render_explorer_page
from src.ui.pages.methodology_page import render_methodology_page
from src.ui.pages.ticker_detail_page import render_ticker_detail_page
from src.ui.pages.admin_page import render_admin_page
from src.utils.logging_utils import get_logger

MYSQL_TARGET_STATE_KEY = "mysql_runtime_target"
LOGGER = get_logger(__name__)

# Kurzer Timeout für schnelle Erreichbarkeitsprüfungen in der UI (Sekunden).
_DB_STATUS_CHECK_TIMEOUT_S = 3


@st.cache_data(ttl=30, show_spinner=False)
def _cached_db_status(
    mysql_uri_local: str,
    mysql_uri_uni: str,
    mongo_uri: str,
    requested_target: str,
) -> tuple[bool, str | None, bool, bool]:
    """Gecachter DB-Erreichbarkeits-Check (TTL 30 s).

    Returns:
        (mysql_connected, active_target, used_fallback, mongo_connected)
    """
    from src.config.settings import load_settings
    from src.db.mongo_client import MongoClientWrapper
    from src.db.mysql_target_resolver import resolve_active_mysql_target

    settings = load_settings()

    mysql_connected = False
    active_target: str | None = None
    used_fallback = False

    # Temporär kürzeren Timeout für Status-Check nutzen
    # Override timeout on target copies via dataclass replace
    from dataclasses import replace as dc_replace
    fast_local = dc_replace(settings.mysql.local_mysql, connect_timeout=_DB_STATUS_CHECK_TIMEOUT_S)
    fast_uni = dc_replace(settings.mysql.uni_mysql, connect_timeout=_DB_STATUS_CHECK_TIMEOUT_S)
    fast_mysql_settings = dc_replace(settings.mysql, local_mysql=fast_local, uni_mysql=fast_uni)

    try:
        result = resolve_active_mysql_target(settings=fast_mysql_settings, requested_target=requested_target)
        mysql_connected = True
        active_target = result.active_target
        used_fallback = result.used_fallback
    except Exception:
        pass

    mongo_connected = False
    try:
        wrapper = MongoClientWrapper(settings.mongo, server_selection_timeout_ms=2000)
        wrapper.get_database().command("ping")
        mongo_connected = True
    except Exception:
        pass

    return mysql_connected, active_target, used_fallback, mongo_connected


def _mask_mongo_uri(uri: str) -> str:
    if "://" in uri and "@" in uri:
        scheme, rest = uri.split("://", 1)
        credentials, host_part = rest.split("@", 1)
        if ":" in credentials:
            username = credentials.split(":", 1)[0]
            return f"{scheme}://{username}:***@{host_part}"
    return uri


def _docker_hint_if_needed(settings: AppSettings) -> str | None:
    compose_path = settings.project_root / "mercator-compose.yml"
    if compose_path.exists():
        return "Did you start MySQL / MongoDB?"
    return None


def _render_database_sidebar_status(
    status_service: DatabaseStatusService, settings: AppSettings, advanced_mode: bool = False
) -> tuple[MySqlResolutionResult | None, DatabaseStatus]:
    """Rendert Sidebar-Steuerung und Status für Datenbanken getrennt."""

    configured_target = settings.mysql.mysql_active_target
    selected_target = st.sidebar.radio(
        "Aktives MySQL-Ziel",
        options=["local", "uni"],
        index=0 if st.session_state.get(MYSQL_TARGET_STATE_KEY, configured_target) == "local" else 1,
        key=MYSQL_TARGET_STATE_KEY,
        horizontal=True,
    )

    # Gecachten DB-Check nutzen (verhindert Blockade beim Seitenrender)
    mysql_connected, active_target, used_fallback, mongo_connected = _cached_db_status(
        mysql_uri_local=f"{settings.mysql.local_mysql.host}:{settings.mysql.local_mysql.port}",
        mysql_uri_uni=f"{settings.mysql.uni_mysql.host}:{settings.mysql.uni_mysql.port}",
        mongo_uri=settings.mongo.uri,
        requested_target=selected_target,
    )

    # Vollständige Auflösung nur wenn tatsächlich verbunden (bereits gecacht / schnell)
    mysql_resolution: MySqlResolutionResult | None = None
    if mysql_connected:
        try:
            _status_full, mysql_resolution = status_service.evaluate(
                mysql_settings=settings.mysql,
                mongo_client=MongoClientWrapper(settings.mongo, server_selection_timeout_ms=2000),
                requested_target=selected_target,
            )
        except Exception:
            mysql_connected = False

    mysql_status = MySqlStatus(
        requested_target=selected_target,
        active_target=active_target if mysql_connected else None,
        is_connected=mysql_connected,
        used_fallback=used_fallback,
        messages=[],
    )
    mongo_status = MongoStatus(
        is_connected=mongo_connected,
        message="MongoDB-Verbindung erfolgreich." if mongo_connected else "MongoDB aktuell nicht erreichbar.",
    )
    status = DatabaseStatus(mysql=mysql_status, mongo=mongo_status)

    with st.sidebar.expander("Datenbank-Status", expanded=advanced_mode):
        if status.mysql.is_connected:
            mysql_text = f"MySQL: verbunden mit `{status.mysql.active_target}`"
            if status.mysql.used_fallback:
                mysql_text += " (Fallback aktiv)"
            st.success(mysql_text)
        else:
            st.warning("MySQL nicht erreichbar. Analysefunktionen eingeschränkt.")

        if status.mongo.is_connected:
            st.success("MongoDB: verbunden")
        else:
            st.warning("MongoDB nicht erreichbar. Rohdatenspeicherung deaktiviert.")

        if not status.mysql.is_connected and not status.mongo.is_connected:
            st.error("Keine Datenbankverbindung verfügbar.")

        docker_hint = _docker_hint_if_needed(settings)
        if docker_hint and (not status.mysql.is_connected or not status.mongo.is_connected):
            st.caption(docker_hint)

    if advanced_mode:
        with st.sidebar.expander("Debug: DB-Status", expanded=False):
            selected_mysql = settings.mysql.get_mysql_target(selected_target)
            st.write(f"MySQL Status: {'connected' if status.mysql.is_connected else 'failed'}")
            st.write(f"MongoDB Status: {'connected' if status.mongo.is_connected else 'failed'}")
            st.write(f"MySQL Host: `{selected_mysql.host}`")
            st.write(f"MySQL Port: `{selected_mysql.port}`")
            st.write(f"MySQL Datenbank: `{selected_mysql.database}`")
            st.write(f"MySQL SSL: `{'deaktiviert' if selected_mysql.ssl_disabled else 'aktiviert'}`")
            st.write(f"Mongo URI: `{_mask_mongo_uri(settings.mongo.uri)}`")
            if mysql_resolution is not None:
                for message in mysql_resolution.messages:
                    st.caption(f"MySQL Detail: {message}")
            elif status.mysql.messages:
                for message in status.mysql.messages:
                    st.caption(f"MySQL Detail: {message}")
            st.caption(f"Mongo Detail: {status.mongo.message}")

    LOGGER.info(
        "runtime_db_status mysql_connected=%s mongo_connected=%s requested_mysql_target=%s",
        status.mysql.is_connected,
        status.mongo.is_connected,
        status.mysql.requested_target,
    )
    return mysql_resolution, status


def _build_services(
    settings: AppSettings,
    mysql_resolution: MySqlResolutionResult | None,
    db_status: DatabaseStatus,
) -> tuple[DashboardService | None, AnalysisService | None, ImportService | None, AppSettingsService]:
    """Initialisiert Repositories und Services für die UI."""
    if mysql_resolution is not None:
        return ServiceFactory.build_all(
            settings,
            mysql_resolution.client,
            mongo_available=db_status.mongo.is_connected,
        )

    # Degraded Mode: Mongo ok / MySQL fail -> nur Ingestion.
    if db_status.mongo.is_connected:
        import_service, runtime_settings_service = ServiceFactory.build_ingestion_only(settings)
        return None, None, import_service, runtime_settings_service

    # Beide DBs down -> nur UI ohne Datenoperationen.
    return None, None, None, AppSettingsService(runtime_repo=None, filter_repo=None, defaults=settings)


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

    dir_map: dict[str, Literal["auto", "local_to_uni", "uni_to_local"]] = {
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




def _inject_global_styles() -> None:
    """Setzt ein ruhiges, konsistentes UI-Grundlayout für Streamlit."""
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f7f8fa;
            color: #111827;
        }
        [data-testid="stAppViewContainer"] .main .block-container {
            max-width: 1360px;
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e5e7eb;
        }
        h1, h2, h3 {
            letter-spacing: -0.01em;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 0.7rem 0.8rem;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def main() -> None:
    """Konfiguriert Navigation und rendert die gewählte Seite."""
    st.set_page_config(page_title="Mercator", layout="wide")
    _inject_global_styles()
    st.sidebar.title("Mercator")
    st.sidebar.caption("Interaktive Datenanwendung für das Modul Datenbanken 2")

    st.sidebar.markdown("### App-Konfiguration")
    advanced_mode = st.sidebar.toggle("Erweiterte Ansicht (Advanced Mode)", value=False)
    st.session_state["advanced_mode"] = advanced_mode
    st.sidebar.markdown("---")

    settings = load_settings()
    if settings.review_mode:
        st.sidebar.warning("Review Mode: Read Only")
        st.warning("Review Instance - Read Only")
    if settings.ui_test_mode:
        st.sidebar.info("UI Test Mode aktiv")

    status_service = DatabaseStatusService()
    mysql_resolution, db_status = _render_database_sidebar_status(status_service, settings, advanced_mode)

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

    if db_status.mysql.is_connected and not (settings.review_mode or settings.disable_import):
        _render_sync_controls(settings, mysql_resolution)
    elif db_status.mysql.is_connected and settings.review_mode:
        st.sidebar.info("Sync im Review Mode deaktiviert.")

    dashboard_service, analysis_service, import_service, runtime_settings_service = _build_services(
        settings,
        mysql_resolution,
        db_status,
    )

    if db_status.mongo.is_connected and import_service is None:
        detail = ServiceFactory.last_import_issue or "Import-Service konnte nicht initialisiert werden."
        st.session_state["import_service_error"] = detail
    else:
        st.session_state.pop("import_service_error", None)

    if not db_status.mysql.is_connected and not db_status.mongo.is_connected:
        st.error("Keine Datenbankverbindung verfügbar.")
        render_methodology_page()
        return

    def _dashboard() -> None:
        render_dashboard_page(dashboard_service, import_service, settings, runtime_settings_service)

    def _explorer() -> None:
        if analysis_service is None:
            st.warning("MySQL nicht erreichbar. Analysefunktionen eingeschränkt.")
            return
        render_explorer_page(analysis_service, runtime_settings_service)

    def _ticker_detail() -> None:
        if analysis_service is None:
            st.warning("MySQL nicht erreichbar. Analysefunktionen eingeschränkt.")
            return
        render_ticker_detail_page(analysis_service)

    def _admin() -> None:
        if mysql_resolution is None:
            st.error("Admin-Panel benötigt MySQL-Verbindung.")
            return
        render_admin_page(settings, mysql_resolution.client, db_status.mongo.is_connected)

    pages = [st.Page(_dashboard, title="Overview", icon=":material/dashboard:", default=True)]
    if analysis_service is not None:
        pages.extend(
            [
                st.Page(_explorer, title="Explorer", icon=":material/table_view:"),
                st.Page(_ticker_detail, title="Detailansicht", icon=":material/insights:"),
            ]
        )
    pages.append(st.Page(render_methodology_page, title="Methodik", icon=":material/schema:"))
    pages.append(st.Page(_admin, title="Admin", icon=":material/admin_panel_settings:"))
    nav = st.navigation(pages)
    nav.run()


if __name__ == "__main__":
    main()
