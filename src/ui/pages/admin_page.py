"""Admin Dashboard für DB-Verwaltung und Datenmanipulationen."""

from __future__ import annotations

import streamlit as st
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from src.config.settings import AppSettings
from src.db.mongo_client import MongoClientWrapper
from src.db.mysql_client import MySqlClient
from src.db.repositories.sync_state_repository import SyncStateRepository, StartupSyncState
from src.services.app_settings_service import AppSettingsService
from src.services.api_usage_service import ApiUsageService
from src.services.database_status_service import DatabaseStatus
from src.services.import_service import ImportService, ImportSummary
from src.services.mysql_sync_service import MySqlSyncService
from src.services.startup_sync_service import StartupSyncService
from src.services.public_share_service import (
    CloudflareQuickTunnelProvider,
    TunnelManager,
    TunnelStatus,
    read_host_tunnel_runtime_state,
)
from src.ui.components.page_scaffold import render_page_header
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)
PUBLIC_SHARE_MANAGER_STATE_KEY = "public_share_manager"


def _public_share_status_message(status: TunnelStatus) -> tuple[str, str]:
    if status == TunnelStatus.RUNNING:
        return "success", "Tunnel läuft."
    if status == TunnelStatus.STARTING:
        return "info", "Tunnel wird gestartet …"
    if status == TunnelStatus.STALE:
        return "warning", "Tunnel ist stale (z. B. öffentliche URL tot) und muss neu gestartet werden."
    if status == TunnelStatus.WARNING:
        return "warning", "Tunnelprozess lebt, aber die öffentliche URL ist nicht erreichbar (Health-Warnungen)."
    if status == TunnelStatus.ERROR:
        return "error", "Tunnel konnte nicht gestartet werden."
    return "caption", "Tunnel ist gestoppt."


def _public_share_error_feedback(session) -> tuple[str, str]:
    message = "Tunnel meldet einen Fehler."
    level = "error"
    hard_public_failure = session.last_public_check_type in {"cloudflare_1033", "cloudflare_530"}
    container_only_public_warning = (
        session.last_process_alive is True
        and session.last_local_healthcheck_ok is True
        and session.last_public_healthcheck_ok is False
        and not hard_public_failure
    )

    if container_only_public_warning:
        message = "Tunnelprozess lebt, aber Public-Health aus Container fehlgeschlagen."
        level = "warning"
    if session.last_process_alive is False:
        message = "Tunnelprozess wurde beendet."
        level = "error"
    if session.last_public_check_type == "cloudflare_1033":
        message = "Cloudflare meldet 1033."
        level = "error"
    if session.last_public_check_type == "cloudflare_530":
        message = "Cloudflare meldet 530."
        level = "error"
    if session.last_local_healthcheck_ok is False:
        message = "Lokale App nicht erreichbar."
        level = "error"
    return level, message


def _get_public_share_manager(settings: AppSettings) -> TunnelManager:
    manager = st.session_state.get(PUBLIC_SHARE_MANAGER_STATE_KEY)
    if isinstance(manager, TunnelManager):
        return manager

    provider = CloudflareQuickTunnelProvider(
        cloudflared_bin=settings.public_share.cloudflared_bin,
        startup_timeout_seconds=settings.public_share.startup_timeout_seconds,
        startup_grace_seconds=settings.public_share.startup_grace_seconds,
        healthcheck_timeout_seconds=settings.public_share.healthcheck_timeout_seconds,
        cloudflared_extra_args=settings.public_share.cloudflared_extra_args,
    )
    manager = TunnelManager(
        provider=provider,
        provider_name=settings.public_share.provider,
        default_local_url=settings.public_share.local_url,
    )
    st.session_state[PUBLIC_SHARE_MANAGER_STATE_KEY] = manager
    return manager


def _resolve_share_file_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root / path


def _build_import_success_message(summary: ImportSummary, force_profile_refresh: bool) -> str:
    base = (
        "Import erfolgreich abgeschlossen. "
        f"Raw neu: {summary.inserted_raw_records}, "
        f"Raw-Duplikate: {summary.skipped_raw_duplicates}, "
        f"Profile frisch geladen: {summary.fetched_profiles}, "
        f"Cache-Hits: {summary.profile_cache_hits}, "
        f"Profilfehler: {summary.profile_failures}."
    )
    if summary.raw_storage_error:
        base = f"{base} WARNUNG: {summary.raw_storage_error}."
    if force_profile_refresh:
        return f"{base} Cache wurde für diesen Lauf ignoriert."
    return base


def _build_import_metrics(summary: ImportSummary) -> list[tuple[str, int]]:
    return [
        ("Feed Records", summary.fetched_feed_records),
        ("Neue Raw Records", summary.inserted_raw_records),
        ("Raw Duplikate", summary.skipped_raw_duplicates),
        ("Upserted Clean", summary.upserted_clean_records),
        ("Enrichment-Kandidaten", summary.symbols_considered_for_enrichment),
        ("API2-Versuche", summary.profile_fetch_attempts),
        ("Profile frisch geladen", summary.fetched_profiles),
        ("Profile aus Cache", summary.profile_cache_hits),
        ("Profilfehler", summary.profile_failures),
    ]

def _humanize_import_error(exc: Exception) -> str:
    """Übersetzt technische Importfehler in UI-taugliche deutsche Meldungen."""
    raw = str(exc)
    if "trade_republic_match_method" in raw and "cannot be null" in raw.lower():
        return (
            "Import abgebrochen: Für das Trade-Republic-Matching fehlen Pflichtwerte "
            "(Zuordnungsmethode). Bitte erneut ausführen; der Importpfad setzt Standardwerte."
        )
    if "530" in raw:
        return (
            "Import fehlgeschlagen: Upstream/API aktuell nicht erreichbar (HTTP 530). "
            "Bitte später erneut versuchen; lokale UI bleibt verfügbar."
        )
    return f"Import fehlgeschlagen: {raw}"


def _push_admin_feedback(kind: str, message: str, details: str | None = None) -> None:
    st.session_state["admin_feedback"] = {
        "kind": kind,
        "message": message,
        "details": details,
    }


def _show_admin_feedback(kind: str, message: str, details: str | None = None) -> None:
    if kind == "success":
        st.success(message)
    elif kind == "warning":
        st.warning(message)
    elif kind == "error":
        st.error(message)
    else:
        st.info(message)
    if details:
        with st.expander("Technische Details", expanded=False):
            st.code(details, language="text")


def _render_admin_feedback() -> None:
    payload = st.session_state.pop("admin_feedback", None)
    if not payload:
        return
    _show_admin_feedback(
        payload.get("kind", "info"),
        payload.get("message", ""),
        payload.get("details"),
    )


def compute_admin_capabilities(
    db_status: DatabaseStatus | None,
    mysql_client: MySqlClient | None,
    mongo_available: bool,
    settings_service: AppSettingsService | None,
) -> dict[str, bool]:
    mysql_online = bool(db_status.mysql.is_connected) if db_status else bool(mysql_client)
    mongo_online = bool(db_status.mongo.is_connected) if db_status else bool(mongo_available)
    return {
        "mysql_online": mysql_online,
        "mongo_online": mongo_online,
        "write_available": mysql_online and mongo_online,
        "persistence_available": bool(settings_service and settings_service.is_persistence_available()),
    }


def should_render_danger_zone(settings: AppSettings, pending_sync: bool) -> bool:
    app_env = str(settings.app_env or "").strip().lower()
    if app_env in {"prod", "production"}:
        return False
    if bool(settings.review_mode or settings.disable_admin_delete):
        return False
    if getattr(settings, "demo_mode", False):
        return False
    if pending_sync:
        return False
    return True


class AdminDashboardService:
    """Service für Admin-Dashboard-Operationen."""

    def __init__(
        self,
        settings: AppSettings,
        mysql_client: MySqlClient | None,
        mongo_available: bool = True,
    ):
        self.settings = settings
        self.mysql_client = mysql_client
        self.mongo_available = mongo_available
        self.mongo_client = None
        if mongo_available:
            try:
                self.mongo_client = MongoClientWrapper(settings.mongo)
            except Exception as e:
                LOGGER.warning("MongoDB nicht verfügbar: %s", e)
                self.mongo_available = False

    def _deletes_blocked(self) -> bool:
        app_env = str(self.settings.app_env or "").strip().lower()
        is_production = app_env in {"prod", "production"}
        demo_mode = bool(getattr(self.settings, "demo_mode", False))
        return bool(
            is_production or self.settings.review_mode or self.settings.disable_admin_delete or demo_mode
        )

    def _local_sync_state_repo(self) -> SyncStateRepository | None:
        try:
            local_client = MySqlClient(self.settings.mysql.get_mysql_target("local"))
            return SyncStateRepository(local_client)
        except Exception:
            return None

    def get_startup_sync_state(self) -> StartupSyncState | None:
        repo = self._local_sync_state_repo()
        if repo is None:
            return None
        try:
            return repo.load()
        except Exception:
            return None

    def run_pending_startup_sync_now(self) -> tuple[bool, str]:
        try:
            local_client = MySqlClient(self.settings.mysql.get_mysql_target("local"))
            uni_client = MySqlClient(self.settings.mysql.get_mysql_target("uni"))
            service = StartupSyncService(
                local_client=local_client,
                uni_client=uni_client,
                sync_state_repo=SyncStateRepository(local_client),
                sync_service=MySqlSyncService(),
                startup_sync_enabled=self.settings.mysql.mysql_startup_sync_enabled,
                stale_minutes=self.settings.mysql.mysql_startup_sync_stale_minutes,
            )
            outcome = service.run_for_start(
                requested_target="uni",
                active_target="uni",
                uni_reachable=True,
            )
            return outcome.success, outcome.message if outcome.success else (outcome.error or outcome.message)
        except Exception as exc:
            return False, str(exc)

    def _pending_sync_blocks_deletes(self) -> bool:
        state = self.get_startup_sync_state()
        return bool(state and state.pending_uni_sync)

    def _blocked_message(self) -> tuple[bool, str]:
        app_env = str(self.settings.app_env or "").strip().lower()
        if app_env in {"prod", "production"}:
            return False, "Loeschaktionen sind in Produktion dauerhaft deaktiviert."
        if getattr(self.settings, "demo_mode", False):
            return False, "Loeschaktionen sind deaktiviert (Demo Mode / Review Mode / MERCATOR_DISABLE_ADMIN_DELETE)."
        return False, "Loeschaktionen sind deaktiviert (Review Mode / MERCATOR_DISABLE_ADMIN_DELETE)."

    @staticmethod
    def _api2_missing_where_clause() -> str:
        """Konsistente Kriterien fuer fehlende/unvollstaendige API2-Profile."""
        return (
            "c.current_symbol IS NOT NULL "
            "AND c.current_symbol <> '' "
            "AND ("
            "COALESCE(c.profile_status, 'NOT_REQUESTED') IN ('NOT_REQUESTED', 'FAILED') "
            "OR COALESCE(c.sector_resolution_status, 'UNRESOLVED') = 'UNRESOLVED' "
            "OR c.sector IS NULL OR TRIM(c.sector) = '' "
            "OR c.market_cap IS NULL"
            ")"
        )

    def count_mysql_api2_missing_candidates(self) -> int:
        """Zaehlt MySQL-Unternehmen, deren API2-Profil fehlt oder unvollstaendig ist."""
        if not self.mysql_client:
            return 0
        try:
            where_clause = self._api2_missing_where_clause()
            sql = f"SELECT COUNT(*) AS missing_count FROM companies c WHERE {where_clause}"
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(sql)
                    result = cursor.fetchone() or {}
                    return int(result.get("missing_count", 0) or 0)
        except Exception as exc:
            LOGGER.warning("count_mysql_api2_missing_candidates Fehler: %s", exc)
            return 0

    def delete_mysql_api2_missing_datasets(self) -> tuple[bool, str]:
        """Loescht Datensaetze mit fehlenden API2-Profilen inkl. zugehoeriger Trade-Referenzen in MySQL."""
        if not self.mysql_client:
            return False, "MySQL-Verbindung nicht verfuegbar."
        if self._deletes_blocked():
            return self._blocked_message()
        if self._pending_sync_blocks_deletes():
            return (
                False,
                "Loeschaktionen blockiert: Es besteht ein offener Startup-Pending-Sync (local -> uni).",
            )

        try:
            where_clause = self._api2_missing_where_clause()
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(f"SELECT COUNT(*) AS missing_count FROM companies c WHERE {where_clause}")
                    missing_count = int((cursor.fetchone() or {}).get("missing_count", 0) or 0)
                    if missing_count == 0:
                        return True, "Keine API2-fehlt-Datensaetze gefunden."

                    cursor.execute(
                        "DELETE t FROM insider_trades t "
                        "INNER JOIN companies c ON c.company_key = t.company_key "
                        f"WHERE {where_clause}"
                    )
                    trades_deleted = int(cursor.rowcount or 0)

                    cursor.execute(
                        "DELETE ts FROM company_trade_stats ts "
                        "INNER JOIN companies c ON c.company_key = ts.company_key "
                        f"WHERE {where_clause}"
                    )
                    stats_deleted = int(cursor.rowcount or 0)

                    cursor.execute(f"DELETE FROM companies c WHERE {where_clause}")
                    companies_deleted = int(cursor.rowcount or 0)
                    conn.commit()

            msg = (
                "API2-fehlt-Cleanup abgeschlossen: "
                f"Unternehmen {companies_deleted}, Trades {trades_deleted}, Stats {stats_deleted}."
            )
            LOGGER.info(msg)
            return True, msg
        except Exception as exc:
            LOGGER.error("delete_mysql_api2_missing_datasets Fehler: %s", exc)
            return False, f"Fehler beim API2-fehlt-Cleanup: {exc}"

    def get_data_issues_snapshot(self, limit: int = 25) -> dict[str, Any]:
        """Liefert Data-Issues für den Admin-Bereich (Dashboard bleibt diagnosefrei)."""
        empty = {
            "tr_not_found_count": 0,
            "exchange_resolution_issues_count": 0,
            "missing_profiles_count": 0,
            "issue_symbols_count": 0,
            "issue_rows": [],
        }
        if not self.mysql_client:
            return empty
        try:
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        """
                        SELECT
                            SUM(CASE WHEN UPPER(COALESCE(t.tr_availability_state, '')) = 'NOT_FOUND' THEN 1 ELSE 0 END) AS tr_not_found_count,
                            SUM(CASE WHEN UPPER(COALESCE(t.trade_republic_match_confidence, '')) IN ('LOW', 'UNKNOWN') THEN 1 ELSE 0 END) AS exchange_resolution_issues_count,
                            COUNT(DISTINCT CASE WHEN UPPER(COALESCE(t.profile_status, '')) <> 'FETCHED' THEN t.symbol_at_trade END) AS missing_profiles_count
                        FROM insider_trades t
                        """
                    )
                    totals = cursor.fetchone() or {}

                    cursor.execute(
                        """
                        SELECT
                            t.symbol_at_trade AS symbol,
                            MAX(CASE WHEN UPPER(COALESCE(t.tr_availability_state, '')) = 'NOT_FOUND' THEN 1 ELSE 0 END) AS tr_not_found,
                            MAX(CASE WHEN UPPER(COALESCE(t.trade_republic_match_confidence, '')) IN ('LOW', 'UNKNOWN') THEN 1 ELSE 0 END) AS exchange_resolution_issue,
                            MAX(CASE WHEN UPPER(COALESCE(t.profile_status, '')) <> 'FETCHED' THEN 1 ELSE 0 END) AS missing_profile,
                            MAX(CASE WHEN c.sector IS NULL OR TRIM(c.sector) = '' THEN 1 ELSE 0 END) AS missing_sector,
                            MAX(CASE WHEN c.market_cap IS NULL THEN 1 ELSE 0 END) AS missing_market_cap
                        FROM insider_trades t
                        LEFT JOIN companies c ON c.company_key = t.company_key
                        WHERE t.symbol_at_trade IS NOT NULL AND t.symbol_at_trade <> ''
                        GROUP BY t.symbol_at_trade
                        HAVING tr_not_found = 1
                            OR exchange_resolution_issue = 1
                            OR missing_profile = 1
                            OR missing_sector = 1
                            OR missing_market_cap = 1
                        ORDER BY t.symbol_at_trade ASC
                        LIMIT %s
                        """,
                        (int(limit),),
                    )
                    raw_rows = cursor.fetchall() or []

            issue_rows: list[dict[str, str]] = []
            for row in raw_rows:
                row_data = row if isinstance(row, dict) else {}
                reasons: list[str] = []
                if bool(row_data.get("tr_not_found")):
                    reasons.append("TR nicht gefunden")
                if bool(row_data.get("exchange_resolution_issue")):
                    reasons.append("Exchange-Aufloesung unsicher")
                if bool(row_data.get("missing_profile")):
                    reasons.append("API2-Profil fehlt")
                if bool(row_data.get("missing_sector")):
                    reasons.append("Sektor fehlt")
                if bool(row_data.get("missing_market_cap")):
                    reasons.append("Market Cap fehlt")
                issue_rows.append({
                    "Symbol": str(row_data.get("symbol") or ""),
                    "Issues": ", ".join(reasons),
                })

            return {
                "tr_not_found_count": int(totals.get("tr_not_found_count", 0) or 0),
                "exchange_resolution_issues_count": int(totals.get("exchange_resolution_issues_count", 0) or 0),
                "missing_profiles_count": int(totals.get("missing_profiles_count", 0) or 0),
                "issue_symbols_count": len(issue_rows),
                "issue_rows": issue_rows,
            }
        except Exception as exc:
            LOGGER.warning("get_data_issues_snapshot Fehler: %s", exc)
            return empty

    def get_mysql_stats(self) -> dict:
        """Holt Statistiken für MySQL-Datenbank."""
        if not self.mysql_client:
            return {}
        try:
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor(dictionary=True) as cursor:
                    stats = {}

                    # Companies count
                    cursor.execute("SELECT COUNT(*) as count FROM companies")
                    stats["companies_count"] = cursor.fetchone()["count"]

                    # Insider trades count
                    cursor.execute("SELECT COUNT(*) as count FROM insider_trades")
                    stats["trades_count"] = cursor.fetchone()["count"]

                    # Filter settings count
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM app_filter_settings"
                    )
                    stats["filter_settings_count"] = cursor.fetchone()["count"]

                    # Runtime preferences count
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM app_runtime_preferences"
                    )
                    stats["runtime_prefs_count"] = cursor.fetchone()["count"]

                    # Database size (in MB)
                    cursor.execute(
                        f"SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as size_mb "
                        f"FROM information_schema.tables WHERE table_schema = DATABASE()"
                    )
                    result = cursor.fetchone()
                    stats["database_size_mb"] = (
                        result["size_mb"] if result["size_mb"] else 0
                    )
                    try:
                        cursor.execute(
                            "SELECT source_url, source_last_refreshed_at, instrument_count, last_error "
                            "FROM trade_republic_universe_meta ORDER BY source_last_refreshed_at DESC LIMIT 1"
                        )
                        stats["trade_republic_meta"] = cursor.fetchone() or {}
                    except Exception:
                        stats["trade_republic_meta"] = {}
                    try:
                        cursor.execute(
                            "SELECT COUNT(*) AS cnt FROM companies "
                            "WHERE COALESCE(trade_republic_universe_status, 'UNKNOWN') = 'UNKNOWN'"
                        )
                        stats["trade_republic_unknown_count"] = int((cursor.fetchone() or {}).get("cnt", 0))
                    except Exception:
                        stats["trade_republic_unknown_count"] = 0
                    try:
                        cursor.execute(
                            "SELECT COUNT(*) AS cnt FROM companies "
                            "WHERE COALESCE(trade_republic_universe_status, 'UNKNOWN') = 'IN_UNIVERSE'"
                        )
                        stats["trade_republic_in_universe_count"] = int((cursor.fetchone() or {}).get("cnt", 0))
                    except Exception:
                        stats["trade_republic_in_universe_count"] = 0

            return stats
        except Exception as e:
            LOGGER.error("Fehler beim Abrufen von MySQL-Statistiken: %s", e)
            return {}

    def get_mongo_stats(self) -> dict:
        """Holt Statistiken für MongoDB."""
        if not self.mongo_available or not self.mongo_client:
            return {}

        try:
            db = self.mongo_client.get_database()
            stats = {}

            # Collection counts
            for collection_name in ["companies", "insider_trades_raw"]:
                collection = db[collection_name]
                stats[f"{collection_name}_count"] = collection.count_documents({})

            latest_trade = db["insider_trades_raw"].find_one(
                {},
                {"imported_at": 1, "fetched_at": 1},
                sort=[("imported_at", -1), ("fetched_at", -1)],
            )
            latest_company = db["companies"].find_one(
                {},
                {"imported_at": 1, "profile_updated_at": 1, "updated_at": 1},
                sort=[("imported_at", -1), ("profile_updated_at", -1), ("updated_at", -1)],
            )
            stats["latest_raw_trade_import_at"] = (
                (latest_trade or {}).get("imported_at")
                or (latest_trade or {}).get("fetched_at")
            )
            stats["latest_raw_company_import_at"] = (
                (latest_company or {}).get("imported_at")
                or (latest_company or {}).get("profile_updated_at")
                or (latest_company or {}).get("updated_at")
            )

            return stats
        except Exception as e:
            LOGGER.error("Fehler beim Abrufen von MongoDB-Statistiken: %s", e)
            return {}

    def clear_mysql_companies(self) -> tuple[bool, str]:
        """Loecht alle Eintraege aus MySQL companies-Tabelle."""
        if not self.mysql_client:
            return False, "MySQL-Verbindung nicht verfuegbar."
        if self._deletes_blocked():
            return self._blocked_message()
        if self._pending_sync_blocks_deletes():
            return (
                False,
                "Loeschaktionen blockiert: Es besteht ein offener Startup-Pending-Sync (local -> uni).",
            )

        try:
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(*) AS ref_count
                        FROM insider_trades t
                        INNER JOIN companies c ON c.company_key = t.company_key
                        """
                    )
                    ref_count = int((cursor.fetchone() or {}).get("ref_count", 0))
                    if ref_count > 0:
                        return (
                            False,
                            "Loeschung abgebrochen: companies ist referenziert (%s insider_trades). "
                            "Loesche zuerst insider_trades oder nutze eine dedizierte Komplettloeschung."
                            % ref_count,
                        )

                    cursor.execute("DELETE FROM companies")
                    deleted_count = cursor.rowcount
                    conn.commit()

            msg = f"{deleted_count} Unternehmen geloescht"
            LOGGER.info("MySQL companies geloescht: %d Eintraege", deleted_count)
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Loeschen von companies: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mysql_trades(self) -> tuple[bool, str]:
        """Loecht alle Eintraege aus MySQL insider_trades-Tabelle."""
        if not self.mysql_client:
            return False, "MySQL-Verbindung nicht verfuegbar."
        if self._deletes_blocked():
            return self._blocked_message()
        if self._pending_sync_blocks_deletes():
            return (
                False,
                "Loeschaktionen blockiert: Es besteht ein offener Startup-Pending-Sync (local -> uni).",
            )

        try:
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM insider_trades")
                    deleted_count = cursor.rowcount
                    conn.commit()

            msg = f"{deleted_count} Insidertrades geloescht"
            LOGGER.info("MySQL insider_trades geloescht: %d Eintraege", deleted_count)
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Loeschen von insider_trades: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mysql_all(self) -> tuple[bool, str]:
        """Loecht alle Daten aus MySQL-Datenbank."""
        if not self.mysql_client:
            return False, "MySQL-Verbindung nicht verfuegbar."
        if self._deletes_blocked():
            return self._blocked_message()
        if self._pending_sync_blocks_deletes():
            return (
                False,
                "Loeschaktionen blockiert: Es besteht ein offener Startup-Pending-Sync (local -> uni).",
            )

        try:
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor() as cursor:
                    tables_to_clear = [
                        "insider_trades",
                        "companies",
                        "app_filter_settings",
                        "app_runtime_preferences",
                    ]
                    total_deleted = 0

                    for table in tables_to_clear:
                        cursor.execute(f"DELETE FROM {table}")
                        total_deleted += cursor.rowcount
                    conn.commit()

            msg = f"MySQL Datenbank geleert: {total_deleted} Eintraege geloescht"
            LOGGER.info("MySQL Datenbank komplett geleert: %d Eintraege", total_deleted)
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Leeren der MySQL-Datenbank: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mongo_companies(self) -> tuple[bool, str]:
        """Loecht alle Eintraege aus MongoDB companies-Collection."""
        if self._deletes_blocked():
            return self._blocked_message()

        if not self.mongo_available or not self.mongo_client:
            return False, "MongoDB nicht verfuegbar"

        try:
            db = self.mongo_client.get_database()
            collection = db["companies"]
            result = collection.delete_many({})

            msg = f"{result.deleted_count} Unternehmen geloescht"
            LOGGER.info("MongoDB companies geleert: %d Dokumente", result.deleted_count)
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Loeschen von MongoDB companies: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mongo_trades(self) -> tuple[bool, str]:
        """Loecht alle Eintraege aus MongoDB insider_trades_raw-Collection."""
        if self._deletes_blocked():
            return self._blocked_message()

        if not self.mongo_available or not self.mongo_client:
            return False, "MongoDB nicht verfuegbar"

        try:
            db = self.mongo_client.get_database()
            collection = db["insider_trades_raw"]
            result = collection.delete_many({})

            msg = f"{result.deleted_count} Insidertrades geloescht"
            LOGGER.info(
                "MongoDB insider_trades_raw geleert: %d Dokumente", result.deleted_count
            )
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Loeschen von MongoDB insider_trades_raw: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mongo_all(self) -> tuple[bool, str]:
        """Loecht alle Daten aus MongoDB."""
        if self._deletes_blocked():
            return self._blocked_message()

        if not self.mongo_available or not self.mongo_client:
            return False, "MongoDB nicht verfuegbar"

        try:
            db = self.mongo_client.get_database()
            collections_to_clear = ["companies", "insider_trades_raw"]
            total_deleted = 0

            for collection_name in collections_to_clear:
                collection = db[collection_name]
                result = collection.delete_many({})
                total_deleted += result.deleted_count

            msg = f"MongoDB Datenbank geleert: {total_deleted} Dokumente geloescht"
            LOGGER.info("MongoDB Datenbank komplett geleert: %d Dokumente", total_deleted)
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Leeren der MongoDB: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def refresh_tr_universe(self) -> tuple[bool, str]:
        """Triggered einen manuellen Refresh des TR-Universums."""
        from src.services.trade_republic_universe_service import TradeRepublicUniverseIngestionService
        ingest = TradeRepublicUniverseIngestionService(self.settings, self.mysql_client)
        success, reason = ingest.refresh_if_stale(force=True)
        if success:
            return True, "Trade Republic Universum erfolgreich aktualisiert."
        return False, f"Refresh nicht durchgefuehrt: {reason}"

    def count_old_mysql_trades(self, older_than_days: int) -> int:
        """Zählt MySQL insider_trades älter als N Tage (nach filing_date)."""
        if not self.mysql_client:
            return 0
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).date()
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) AS cnt FROM insider_trades WHERE filing_date < %s",
                        (cutoff,),
                    )
                    return int((cursor.fetchone() or {}).get("cnt", 0))
        except Exception as e:
            LOGGER.warning("count_old_mysql_trades Fehler: %s", e)
            return 0

    def delete_old_mysql_trades(self, older_than_days: int) -> tuple[bool, str]:
        """Löscht MySQL insider_trades älter als N Tage (nach filing_date)."""
        if not self.mysql_client:
            return False, "MySQL-Verbindung nicht verfügbar."
        if self._deletes_blocked():
            return self._blocked_message()
        if self._pending_sync_blocks_deletes():
            return False, "Löschaktionen blockiert: offener Pending-Sync."
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).date()
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM insider_trades WHERE filing_date < %s",
                        (cutoff,),
                    )
                    deleted = cursor.rowcount
                    conn.commit()
            msg = f"{deleted} Insider-Trades (filing_date vor {cutoff}) gelöscht."
            LOGGER.info("Old MySQL trades deleted: %d (cutoff=%s)", deleted, cutoff)
            return True, msg
        except Exception as e:
            LOGGER.error("delete_old_mysql_trades Fehler: %s", e)
            return False, f"Fehler beim Löschen alter Trades: {e}"

    def count_old_mongo_trades(self, older_than_days: int) -> int:
        """Zählt MongoDB insider_trades_raw-Dokumente älter als N Tage (nach filing_date)."""
        if not self.mongo_available or not self.mongo_client:
            return 0
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            db = self.mongo_client.get_database()
            col = db["insider_trades_raw"]
            return col.count_documents({"filing_date": {"$lt": cutoff.strftime("%Y-%m-%d")}})
        except Exception as e:
            LOGGER.warning("count_old_mongo_trades Fehler: %s", e)
            return 0

    def delete_old_mongo_trades(self, older_than_days: int) -> tuple[bool, str]:
        """Löscht MongoDB insider_trades_raw-Dokumente älter als N Tage."""
        if self._deletes_blocked():
            return self._blocked_message()
        if not self.mongo_available or not self.mongo_client:
            return False, "MongoDB nicht verfügbar."
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            cutoff_str = cutoff.strftime("%Y-%m-%d")
            db = self.mongo_client.get_database()
            col = db["insider_trades_raw"]
            result = col.delete_many({"filing_date": {"$lt": cutoff_str}})
            msg = f"{result.deleted_count} Raw-Trades (filing_date vor {cutoff_str}) gelöscht."
            LOGGER.info("Old Mongo trades deleted: %d (cutoff=%s)", result.deleted_count, cutoff_str)
            return True, msg
        except Exception as e:
            LOGGER.error("delete_old_mongo_trades Fehler: %s", e)
            return False, f"Fehler beim Löschen alter MongoDB-Trades: {e}"

    def rebuild_mysql_schema(self) -> tuple[bool, str]:
        """Initialisiert/repariert das MySQL-Schema."""
        if not self.mysql_client:
            return False, "MySQL-Verbindung nicht verfuegbar."
        try:
            actions = self.mysql_client.initialize_schema()
            if not actions:
                msg = "Schema ist aktuell. Keine Aenderungen noetig."
            else:
                msg = f"Schema aktualisiert: {len(actions)} Aenderungen\n\n"
                for action in actions:
                    msg += f"  - {action}\n"
            LOGGER.info("MySQL-Schema aktualisiert")
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Schema-Update: {e}"
            LOGGER.error(error_msg)
            return False, error_msg


def render_admin_page(
    settings: AppSettings,
    mysql_client: MySqlClient | None,
    mongo_available: bool = True,
    db_status: DatabaseStatus | None = None,
    settings_service: AppSettingsService | None = None,
    import_service: ImportService | None = None,
    api_usage_service: ApiUsageService | None = None,
) -> None:
    """Rendert die Admin-Seite als präzisen Regelarbeitsplatz."""

    capabilities = compute_admin_capabilities(db_status, mysql_client, mongo_available, settings_service)
    mysql_online = capabilities["mysql_online"]
    mongo_online = capabilities["mongo_online"]
    write_available = capabilities["write_available"]
    persistence_available = capabilities["persistence_available"]

    if not write_available:
        st.info(
            "Admin-Funktionen laufen im Lesemodus. Schreibende und destruktive Aktionen sind vorübergehend deaktiviert."
        )
    if settings_service and not persistence_available:
        st.info("Einstellungen im Admin-Bereich werden derzeit nur für diese Sitzung übernommen.")
    if str(settings.app_env or "").strip().lower() in {"prod", "production"}:
        st.info("Produktionsmodus aktiv: Destruktive Datenbank-Aktionen sind serverseitig deaktiviert.")
    _render_admin_feedback()

    # 0. HEADER MIT SYSTEM-CHECK
    actions = [{"label": "System-Check", "type": "secondary"}]
    results = render_page_header(
        "Admin", 
        "Konfiguration von Gates, Scoring-Regeln und Datenquellen.",
        actions=actions
    )
    
    if results and results[0]:
        st.session_state["show_system_check"] = True

    if st.session_state.get("show_system_check", False):
        with st.container(border=True):
            st.markdown("### System-Verfügbarkeit")
            c1, c2 = st.columns(2)
            if mysql_online:
                c1.success("MySQL: Online")
            else:
                c1.error("MySQL: Offline")
            
            if mongo_online:
                c2.success("MongoDB: Online")
            else:
                c2.warning("MongoDB: Nicht verfügbar")
            
            if st.button("Schließen", use_container_width=True):
                st.session_state["show_system_check"] = False
                st.rerun()

    # 1. Hauptnavigation über echte Tabs (Requirement 8.2)
    tab_import, tab_sync, tab_db_control, tab_public_share = st.tabs([
        "Import und API2", "Sync-Status", "Datenbank-Kontrolle", "Öffentliche Freigabe"
    ])

    admin_service = AdminDashboardService(settings, mysql_client, mongo_available)
    startup_sync_state = admin_service.get_startup_sync_state()
    pending_startup_sync = bool(startup_sync_state and startup_sync_state.pending_uni_sync)

    # 2. IMPORT & API2 TAB
    with tab_import:
        st.subheader("Datenimport & API2-Steuerung")
        
        # A. API Usage Sektion
        if api_usage_service:
            usage = api_usage_service.get_current_usage()
            st.markdown("#### API-Nutzung (heute)")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Calls heute", usage["call_count"])
            c2.metric("Limit heute", usage["limit_count"])
            c3.metric("Restbudget", usage["remaining"], delta=None if usage["remaining"] > 10 else -usage["call_count"], delta_color="normal")
            
            last_req = usage.get("last_request_at")
            last_req_str = last_req.strftime("%H:%M:%S") if last_req else "Keine"
            c4.metric("Letzter Request", last_req_str)
            st.caption("FMP API Kontingent (250 Calls/Tag). Reset erfolgt automatisch um Mitternacht.")

        st.markdown("---")

        if settings_service:
            runtime_settings = settings_service.load()
            
            col_config, col_scheduler = st.columns(2)
            
            with col_config:
                with st.form("api2_config_form", border=True):
                    st.markdown("#### Import Konfiguration")
                    api2_mode = st.selectbox(
                        "API2-Firing Mode",
                        options=["ONLY PASS", "PASS + PENDING", "ALL TRADED COMPANIES", "DISABLED"],
                        index=["ONLY PASS", "PASS + PENDING", "ALL TRADED COMPANIES", "DISABLED"].index(runtime_settings.api2_firing_mode) if runtime_settings.api2_firing_mode in ["ONLY PASS", "PASS + PENDING", "ALL TRADED COMPANIES", "DISABLED"] else 0,
                        help=(
                            "ONLY PASS: Enrichment nur für PASS-Trades. "
                            "PASS + PENDING: Für PASS und PENDING. "
                            "ALL TRADED COMPANIES: Alle gehandelten Unternehmen werden als Kandidaten geprüft. "
                            "Cache/TTL gelten weiterhin, sofern kein manueller Force-Refresh aktiviert ist. "
                            "DISABLED: Kein Enrichment."
                        ),
                    )
                    
                    import_page = st.number_input("Feed-Seite (Standard 0)", min_value=0, value=0, help="Free-Tier Zugang kann auf Seite 0 beschränkt sein.")
                    import_limit = st.number_input("Records pro Seite", min_value=1, max_value=1000, value=100)
                    
                    submit_label = "Konfiguration speichern" if persistence_available else "Konfiguration für diese Sitzung übernehmen"
                    if st.form_submit_button(submit_label, use_container_width=True):
                        runtime_settings.api2_firing_mode = api2_mode
                        settings_service.save(runtime_settings)
                        _push_admin_feedback(
                            "success",
                            "Konfiguration gespeichert." if persistence_available else "Konfiguration für diese Sitzung übernommen.",
                        )
                        st.rerun()

            with col_scheduler:
                with st.form("scheduler_config_form", border=True):
                    st.markdown("#### Auto-Import Scheduler")
                    auto_enabled = st.toggle("Auto-Import aktiv", value=runtime_settings.auto_import_enabled)
                    auto_interval = st.number_input("Intervall (Minuten)", min_value=1, value=runtime_settings.auto_import_interval_minutes)
                    auto_on_start = st.toggle("Initial Import beim Start", value=runtime_settings.auto_import_on_start)
                    
                    submit_label = "Scheduler speichern" if persistence_available else "Scheduler für diese Sitzung übernehmen"
                    if st.form_submit_button(submit_label, use_container_width=True):
                        runtime_settings.auto_import_enabled = auto_enabled
                        runtime_settings.auto_import_interval_minutes = auto_interval
                        runtime_settings.auto_import_on_start = auto_on_start
                        settings_service.save(runtime_settings)
                        _push_admin_feedback(
                            "success",
                            "Scheduler-Einstellungen gespeichert." if persistence_available else "Scheduler-Einstellungen für diese Sitzung übernommen.",
                        )
                        st.rerun()
                
                # Scheduler Status
                if runtime_settings.auto_import_enabled:
                    st.info("Scheduler ist AKTIV")
                    if runtime_settings.last_auto_import_at:
                        last_ts = datetime.fromisoformat(runtime_settings.last_auto_import_at)
                        next_ts = last_ts + timedelta(minutes=runtime_settings.auto_import_interval_minutes)
                        st.write(f"Letzter: {last_ts.strftime('%H:%M:%S')}")
                        st.write(f"Nächster: {next_ts.strftime('%H:%M:%S')}")
                        
                        remaining = next_ts - datetime.now(timezone.utc)
                        if remaining.total_seconds() > 0:
                            st.write(f"Countdown: {int(remaining.total_seconds() // 60)}m {int(remaining.total_seconds() % 60)}s")
                        else:
                            st.write("Fällig: Sofort")
                else:
                    st.warning("Scheduler ist DEAKTIVIERT")

        st.markdown("---")
        st.markdown("#### Manueller Import")
        api2_missing_count = admin_service.count_mysql_api2_missing_candidates() if mysql_online else 0
        st.caption(
            "Bulk-Backfill fuer fehlende API2-Profile: "
            f"aktuell {api2_missing_count} Kandidaten in MySQL."
        )
        backfill_limit = st.number_input(
            "API2-Backfill Batch-Größe",
            min_value=10,
            max_value=300,
            value=50,
            step=10,
            help="Anzahl Kandidaten mit API2 fehlt/Unknown, die pro Backfill-Lauf nachgeladen werden.",
            disabled=not write_available,
        )
        if st.button(
            "API2-Backfill jetzt ausführen",
            use_container_width=True,
            disabled=(not write_available) or (import_service is None),
            help=None if write_available else "Backfill ist deaktiviert, solange MySQL oder MongoDB nicht verfügbar sind.",
        ):
            if not import_service:
                _show_admin_feedback("error", "Import-Service nicht verfügbar.")
            else:
                with st.spinner("Lade fehlende API2-Profile nach..."):
                    try:
                        summary = import_service.backfill_missing_profiles(max_symbols=int(backfill_limit), force_refresh=True)
                        _show_admin_feedback(
                            "success",
                            (
                                f"API2-Backfill abgeschlossen: Kandidaten {summary.candidates}, "
                                f"versucht {summary.attempted}, aktualisiert {summary.refreshed}, Fehler {summary.failed}."
                            ),
                        )
                    except Exception as e:
                        _show_admin_feedback("error", "API2-Backfill fehlgeschlagen.", str(e))

        raw_sync_limit = st.number_input(
            "Raw->Clean Sync Limit",
            min_value=10,
            max_value=1000,
            value=100,
            step=10,
            help="Anzahl der neuesten Raw-Trades aus MongoDB, die ohne API-Call nach MySQL synchronisiert werden.",
            disabled=(not write_available) or (import_service is None),
            key="admin_raw_clean_sync_limit",
        )
        if st.button(
            "Raw -> Clean Sync ausführen",
            use_container_width=True,
            disabled=(not write_available) or (import_service is None),
            help=None if write_available else "Sync ist deaktiviert, solange MySQL oder MongoDB nicht verfügbar sind.",
            key="admin_run_raw_clean_sync",
        ):
            if not import_service:
                _show_admin_feedback("error", "Import-Service nicht verfügbar.")
            else:
                with st.spinner("Synchronisiere Raw-Daten nach Clean-Store..."):
                    try:
                        sync_summary = import_service.sync_raw_to_clean(limit=int(raw_sync_limit))
                        _show_admin_feedback(
                            "success",
                            (
                                "Raw->Clean-Sync abgeschlossen: "
                                f"Raw-Kandidaten {sync_summary.raw_candidates}, "
                                f"Clean-Upserts {sync_summary.clean_upserted}, "
                                f"übersprungen ohne dedupe_key {sync_summary.skipped_missing_dedupe}."
                            ),
                        )
                    except Exception as e:
                        _show_admin_feedback("error", "Raw->Clean-Sync fehlgeschlagen.", str(e))

        confirm_api2_cleanup = st.checkbox(
            "Ich bestaetige: API2-fehlt-Datensaetze in MySQL loeschen (inkl. zugehoeriger Trades/Stats)",
            value=False,
            key="admin_confirm_api2_missing_cleanup",
            disabled=not mysql_online,
        )
        if st.button(
            "Alle API2-fehlt-Datensaetze loeschen",
            use_container_width=True,
            disabled=(not mysql_online) or (api2_missing_count <= 0) or (not confirm_api2_cleanup),
            help=(
                "Nur verfuegbar mit MySQL-Verbindung, vorhandenen Kandidaten und bestaetigter Checkbox."
                if mysql_online
                else "Loeschung ist nur bei aktiver MySQL-Verbindung verfuegbar."
            ),
        ):
            success, message = admin_service.delete_mysql_api2_missing_datasets()
            if success:
                _show_admin_feedback("success", message)
                st.rerun()
            else:
                _show_admin_feedback("error", message)

        force_profile_refresh = st.checkbox(
            "Profil-Refresh erzwingen",
            value=False,
            help=(
                "Ignoriert den Profil-Cache für diesen manuellen Import und ruft API2 erneut auf. "
                "Vorsicht: erhöht API-Verbrauch."
            ),
            disabled=not write_available,
        )
        if st.button(
            "Manuellen Import jetzt starten",
            type="primary",
            use_container_width=True,
            disabled=not write_available,
            help=None if write_available else "Import ist deaktiviert, solange MySQL oder MongoDB nicht verfügbar sind.",
        ):
            if not import_service:
                _show_admin_feedback("error", "Import-Service nicht verfügbar.")
            else:
                with st.spinner("Importiere Daten von FMP..."):
                    try:
                        # Hier nutzen wir die aktuell im Formular (bzw. state) stehenden Werte falls nötig, 
                        # oder einfach die gespeicherten Defaults. 
                        # Da das Formular oben 'save' erzwingt, nehmen wir einfach die aus runtime_settings.
                        summary = import_service.run_hourly_import(
                            page=int(import_page if 'import_page' in locals() else 0),
                            limit=int(import_limit if 'import_limit' in locals() else 100),
                            force_profile_refresh=force_profile_refresh,
                        )
                        _show_admin_feedback("success", _build_import_success_message(summary, force_profile_refresh=force_profile_refresh))
                        if summary.profile_failures > 0:
                            _show_admin_feedback(
                                "warning",
                                "Einzelne Profilabrufe sind fehlgeschlagen. "
                                "Der Import wurde fortgesetzt; Details siehe Kennzahlen unten."
                            )
                        
                        # Import Summary Sektion
                        st.markdown("##### Import Zusammenfassung")
                        metrics = _build_import_metrics(summary)
                        columns = st.columns(4)
                        for idx, (label, value) in enumerate(metrics):
                            columns[idx % 4].metric(label, value)
                        st.balloons()
                    except Exception as e:
                        _show_admin_feedback("error", _humanize_import_error(e), str(e))

    # 3. SYNC STATUS TAB
    with tab_sync:
        st.subheader("Synchronisations-Status")
        st.caption("Status von MongoDB Raw Store, MySQL Clean Store und Local -> Uni Clean-Sync.")

        col1, col2 = st.columns(2)
        mysql_stats = admin_service.get_mysql_stats()
        mongo_stats = admin_service.get_mongo_stats()
        
        with col1:
            st.markdown("#### MySQL Clean Store")
            st.metric("Trades", f"{mysql_stats.get('trades_count', 0):,}")
            st.metric("Companies", f"{mysql_stats.get('companies_count', 0):,}")
            st.metric("Größe (MB)", f"{mysql_stats.get('database_size_mb', 0):.2f}")
            
        with col2:
            st.markdown("#### MongoDB Raw Store")
            st.metric("Raw Trades", f"{mongo_stats.get('insider_trades_raw_count', 0):,}")
            st.metric("Raw Companies", f"{mongo_stats.get('companies_count', 0):,}")
            st.caption(f"Letzter Raw-Trade-Import: {mongo_stats.get('latest_raw_trade_import_at') or '-'}")
            st.caption(f"Letzter Raw-Company-Import: {mongo_stats.get('latest_raw_company_import_at') or '-'}")

        raw_trades_count = int(mongo_stats.get("insider_trades_raw_count", 0) or 0)
        clean_trades_count = int(mysql_stats.get("trades_count", 0) or 0)
        raw_status = "UNAVAILABLE" if not mongo_online else ("EMPTY" if raw_trades_count == 0 else "OK")
        st.caption(f"Raw-Store-Status: {raw_status}")
        if raw_status == "EMPTY":
            st.warning(
                "Raw Store ist leer. Fuehre einen echten Import aus. "
                "Clean-Daten allein erfuellen den Raw-Nachweis nicht."
            )
        if clean_trades_count > 0 and raw_trades_count == 0:
            st.info("Naechster Schritt: Import starten und danach Raw/Clean-Counts erneut pruefen.")

        st.markdown("---")
        st.markdown("#### Data Issues (Admin-only)")
        data_issues = admin_service.get_data_issues_snapshot(limit=25) if mysql_online else None
        if not mysql_online:
            st.info("Data-Issues-Diagnose ist nur mit aktiver MySQL-Verbindung verfuegbar.")
        else:
            di1, di2, di3, di4 = st.columns(4)
            di1.metric("TR nicht gefunden", f"{int((data_issues or {}).get('tr_not_found_count', 0)):,}")
            di2.metric("Exchange-Issues", f"{int((data_issues or {}).get('exchange_resolution_issues_count', 0)):,}")
            di3.metric("Fehlende Profile", f"{int((data_issues or {}).get('missing_profiles_count', 0)):,}")
            di4.metric("Symbole mit Issues", f"{int((data_issues or {}).get('issue_symbols_count', 0)):,}")
            issue_rows = (data_issues or {}).get("issue_rows", [])
            if issue_rows:
                st.dataframe(issue_rows, use_container_width=True, hide_index=True)
            else:
                st.caption("Keine Data-Issues erkannt.")

        st.markdown("---")
        st.markdown("#### MySQL Local -> Uni Sync")
        s1, s2, s3 = st.columns(3)
        with s1:
            st.metric("Pending Uni Sync", "Ja" if pending_startup_sync else "Nein")
            st.caption(f"Letzter Startmodus: {(startup_sync_state.last_start_mode if startup_sync_state else '-')}")
            st.caption(f"Requested Target: {(startup_sync_state.last_requested_target if startup_sync_state else '-')}")
        with s2:
            st.caption(f"Aktiver Target: {(startup_sync_state.last_active_target if startup_sync_state else '-')}")
            st.caption(f"Letzter Auto-Sync Status: {(startup_sync_state.last_sync_status if startup_sync_state else '-')}")
            st.caption(f"Richtung: {(startup_sync_state.last_sync_direction if startup_sync_state else '-')}")
        with s3:
            last_ok = startup_sync_state.last_successful_uni_sync_at if startup_sync_state else None
            st.caption(f"Letzter erfolgreicher Uni-Sync: {last_ok or '-'}")
            st.caption(f"Letzter Fehler: {(startup_sync_state.last_sync_error if startup_sync_state else '-')}")

        if pending_startup_sync:
            st.warning(
                "Die App wurde zuletzt ohne aktive Uni-DB betrieben. Beim nächsten Uni-Start wird oder wurde ein local -> uni Sync ausgeführt."
            )
            if st.button("Pending Startup Sync jetzt ausführen", use_container_width=False):
                success, message = admin_service.run_pending_startup_sync_now()
                if success:
                    _push_admin_feedback("success", message)
                else:
                    _push_admin_feedback("error", "Pending Startup Sync fehlgeschlagen.", message)
                st.rerun()

    # 4. DB CONTROL TAB
    with tab_db_control:
        st.subheader("Datenbank-Wartung & Resets")
        st.caption("Technische Werkzeuge zur Fehlerbehebung und Datenbereinigung.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Wartung")
            if st.button(
                "Schema reparieren",
                use_container_width=True,
                help="Initialisiert oder aktualisiert das Tabellen-Schema in MySQL",
                disabled=not mysql_online,
            ):
                with st.spinner("Repariere Schema..."):
                    success, msg = admin_service.rebuild_mysql_schema()
                    if success:
                        _push_admin_feedback("success", msg)
                    else:
                        _push_admin_feedback("error", "Schema-Reparatur fehlgeschlagen.", msg)
                    st.rerun()
            
            if st.button(
                "TR-Universum aktualisieren",
                use_container_width=True,
                help="Aktualisiert die Liste der handelbaren Ticker von Trade Republic",
                disabled=not write_available,
            ):
                with st.spinner("Aktualisiere TR-Universum..."):
                    success, msg = admin_service.refresh_tr_universe()
                    if success:
                        _push_admin_feedback("success", msg)
                    else:
                        _push_admin_feedback("warning", "TR-Universum konnte nicht vollständig aktualisiert werden.", msg)
                    st.rerun()
        
        with c2:
            st.markdown("#### Gefahrenzone")
            danger_zone_visible = should_render_danger_zone(settings, pending_startup_sync)
            if not danger_zone_visible:
                st.info("Destruktive Datenbankaktionen sind in dieser Umgebung deaktiviert.")
            else:
                with st.popover("MySQL-Daten löschen", use_container_width=True):
                    if not mysql_online:
                        st.info("Löschfunktionen für MySQL sind nur bei aktiver MySQL-Verbindung verfügbar.")
                    if pending_startup_sync:
                        st.warning("Löschaktionen blockiert, solange ein Pending Startup Sync offen ist.")
                    st.error("### ACHTUNG: Datenverlust")
                    st.write("Dies löscht alle verarbeiteten Insider-Trades und Firmendaten in MySQL.")
                    st.write("Rohdaten in MongoDB bleiben erhalten.")
                    
                    confirm_mysql = st.checkbox("Ich bin mir der Konsequenzen bewusst", key="confirm_mysql_delete_final_v2")
                    if st.button(
                        "JETZT MySQL LÖSCHEN",
                        type="primary",
                        use_container_width=True,
                        disabled=(not confirm_mysql) or (not mysql_online) or pending_startup_sync,
                    ):
                        with st.spinner("Lösche MySQL Daten..."):
                            success, msg = admin_service.clear_mysql_all()
                            if success:
                                _show_admin_feedback("success", msg)
                                st.rerun()
                            else:
                                _show_admin_feedback("error", msg)

                with st.popover("MongoDB-Rohdaten löschen", use_container_width=True):
                    if not mongo_online:
                        st.info("Löschfunktionen für MongoDB sind nur bei aktiver MongoDB-Verbindung verfügbar.")
                    st.error("### KRITISCHE AKTION: Rohdatenverlust")
                    st.write("Dies löscht alle importierten Rohdaten in MongoDB.")
                    st.caption("Diese Aktion ist bewusst nur im Adminbereich und mit expliziter Bestätigung erreichbar.")

                    confirm_mongo = st.checkbox("Ich möchte wirklich alle Rohdaten löschen", key="confirm_mongo_delete_final_v2")
                    if st.button(
                        "JETZT MongoDB LÖSCHEN",
                        type="primary",
                        use_container_width=True,
                        disabled=(not confirm_mongo) or (not mongo_online),
                    ):
                        with st.spinner("Lösche MongoDB Daten..."):
                            success, msg = admin_service.clear_mongo_all()
                            if success:
                                _show_admin_feedback("success", msg)
                                st.rerun()
                            else:
                                _show_admin_feedback("error", msg)

        # --- Alte Datensätze bereinigen ---
        if should_render_danger_zone(settings, pending_startup_sync):
            st.markdown("---")
            st.markdown("#### 🗂️ Alte Datensätze bereinigen")
            st.caption(
                "Löscht Insider-Trades, deren Filing-Datum älter als der gewählte Schwellenwert ist. "
                "Sinnvoll ab ca. 12–24 Monaten: Ältere Trades sind für die laufende Analyse irrelevant, "
                "belasten die DB-Performance und erhöhen den Sync-Aufwand. "
                "Unternehmensdaten (companies) werden **nicht** berührt."
            )

            col_thresh, col_preview = st.columns([1, 1])
            with col_thresh:
                retention_days = st.number_input(
                    "Aufbewahrungsdauer (Tage)",
                    min_value=30,
                    max_value=3650,
                    value=365,
                    step=30,
                    help="Trades mit filing_date älter als dieser Wert werden gelöscht. Standard: 365 Tage (1 Jahr).",
                    disabled=not write_available,
                    key="retention_days_input",
                )

            with col_preview:
                if st.button(
                    "Vorschau: Wie viele Datensätze wären betroffen?",
                    use_container_width=True,
                    disabled=not write_available,
                    key="retention_preview_btn",
                ):
                    mysql_old = admin_service.count_old_mysql_trades(int(retention_days))
                    mongo_old = admin_service.count_old_mongo_trades(int(retention_days))
                    st.session_state["retention_preview"] = {
                        "days": int(retention_days),
                        "mysql": mysql_old,
                        "mongo": mongo_old,
                    }

            if preview := st.session_state.get("retention_preview"):
                cutoff_date = (datetime.now(timezone.utc) - timedelta(days=preview["days"])).date()
                p1, p2 = st.columns(2)
                p1.metric(f"MySQL Trades vor {cutoff_date}", f"{preview['mysql']:,}")
                p2.metric(f"MongoDB Raw-Trades vor {cutoff_date}", f"{preview['mongo']:,}")

            with st.popover("Alte Trades löschen", use_container_width=True):
                st.warning(
                    f"Es werden Insider-Trades gelöscht, deren filing_date älter als **{int(st.session_state.get('retention_days_input', 365))} Tage** ist."
                )
                st.info(
                    "💡 **Empfehlung:** 365 Tage (1 Jahr) ist ein guter Standard. "
                    "Trades < 6 Monate löschen ist riskant, da sie noch aktiv gehandelt werden könnten. "
                    "Für langfristige Analyse empfiehlt sich ≥ 730 Tage."
                )
                confirm_old_mysql = st.checkbox("MySQL: Alte Trades löschen bestätigen", key="confirm_old_mysql")
                confirm_old_mongo = st.checkbox("MongoDB: Alte Raw-Trades ebenfalls löschen", key="confirm_old_mongo")

                col_del1, col_del2 = st.columns(2)
                with col_del1:
                    if st.button(
                        "MySQL alte Trades löschen",
                        type="primary",
                        use_container_width=True,
                        disabled=(not confirm_old_mysql) or (not mysql_online) or pending_startup_sync,
                        key="btn_del_old_mysql",
                    ):
                        days_val = int(st.session_state.get("retention_days_input", 365))
                        with st.spinner(f"Lösche MySQL-Trades älter als {days_val} Tage …"):
                            success, msg = admin_service.delete_old_mysql_trades(days_val)
                            st.session_state.pop("retention_preview", None)
                            if success:
                                _push_admin_feedback("success", msg)
                            else:
                                _push_admin_feedback("error", "Löschen fehlgeschlagen.", msg)
                            st.rerun()

                with col_del2:
                    if st.button(
                        "MongoDB alte Raw-Trades löschen",
                        use_container_width=True,
                        disabled=(not confirm_old_mongo) or (not mongo_online),
                        key="btn_del_old_mongo",
                    ):
                        days_val = int(st.session_state.get("retention_days_input", 365))
                        with st.spinner(f"Lösche MongoDB Raw-Trades älter als {days_val} Tage …"):
                            success, msg = admin_service.delete_old_mongo_trades(days_val)
                            st.session_state.pop("retention_preview", None)
                            if success:
                                _push_admin_feedback("success", msg)
                            else:
                                _push_admin_feedback("error", "Löschen fehlgeschlagen.", msg)
                            st.rerun()
        else:
            st.caption("Retention-Löschfunktionen sind in dieser Umgebung deaktiviert.")

    # 5. OEFFENTLICHE FREIGABE
    with tab_public_share:
        st.subheader("Öffentliche Freigabe")
        if not settings.public_share.enabled:
            st.caption("Die Funktion ist über ENABLE_PUBLIC_SHARE=false deaktiviert.")
        else:
            execution_mode = settings.public_share.execution_mode
            manager = _get_public_share_manager(settings) if execution_mode == "container" else None
            session = manager.get_session() if manager else None
            provider = manager.provider if manager else None

            st.warning(
                "Nur für lokale Demo/Test-Freigaben nutzen. Die öffentliche URL ist extern erreichbar."
            )
            st.caption(f"Execution Mode: {execution_mode}")

            if execution_mode == "host":
                status_file = _resolve_share_file_path(settings.project_root, settings.public_share.status_file)
                log_file = _resolve_share_file_path(settings.project_root, settings.public_share.log_file)
                pid_file = _resolve_share_file_path(settings.project_root, settings.public_share.pid_file)
                host_state = read_host_tunnel_runtime_state(
                    status_file=str(status_file),
                    log_file=str(log_file),
                    pid_file=str(pid_file),
                    default_provider=settings.public_share.provider,
                    default_local_url=settings.public_share.local_url,
                )

                with st.container(border=True):
                    st.info(
                        "Host-Modus aktiv: cloudflared läuft außerhalb des Containers. "
                        "Dieser Pfad ist für Cloudflare Quick Tunnel der empfohlene Standard."
                    )
                    st.code(
                        ".\\mercator.ps1 share-start\n.\\mercator.ps1 share-status\n.\\mercator.ps1 share-reset\n.\\mercator.ps1 share-stop\n.\\mercator.ps1 share-logs",
                        language="powershell",
                    )
                    cols = st.columns(2)
                    with cols[0]:
                        st.text_input("Provider", value=host_state.provider, disabled=True)
                        st.text_input("Lokale Ziel-URL", value=host_state.local_url, disabled=True)
                        st.text_input("Status", value=host_state.status.value, disabled=True)
                        st.text_input("Prozess lebt", value="Ja" if host_state.process_alive else "Nein", disabled=True)
                        st.text_input("PID", value=str(host_state.pid) if host_state.pid is not None else "-", disabled=True)
                    with cols[1]:
                        started_at = (
                            host_state.started_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                            if host_state.started_at
                            else "-"
                        )
                        st.text_input("Startzeit", value=started_at, disabled=True)
                        st.text_input("Öffentliche URL", value=host_state.public_url or "-", disabled=True)
                        st.text_input(
                            "Exit-Code",
                            value=str(host_state.last_exit_code) if host_state.last_exit_code is not None else "-",
                            disabled=True,
                        )
                        st.text_input("Letzter Fehler", value=host_state.last_error or "-", disabled=True)
                        st.text_input("Extra-Args", value=" ".join(host_state.extra_args) or "-", disabled=True)

                can_open_host = bool(host_state.public_url and host_state.status == TunnelStatus.RUNNING)
                st.link_button(
                    "Öffentliche URL öffnen",
                    host_state.public_url if can_open_host and host_state.public_url else "http://localhost",
                    disabled=not can_open_host,
                    use_container_width=True,
                )
                if host_state.status == TunnelStatus.WARNING:
                    _show_admin_feedback(
                        "warning",
                        "Die aktuelle Tunnel-URL ist nicht stabil erreichbar.",
                        "Bitte nicht die bestehende trycloudflare-URL weitergeben. Stattdessen `share-reset` ausführen "
                        "und nur die frisch erzeugte URL verwenden.",
                    )
                if host_state.status == TunnelStatus.STALE:
                    _show_admin_feedback(
                        "warning",
                        "Die gespeicherte Tunnel-URL ist veraltet.",
                        "Bitte `share-reset` ausführen. Alte trycloudflare-Links bleiben dauerhaft ungültig.",
                    )
                st.markdown("##### Letzter Log-Ausschnitt")
                if host_state.log_tail:
                    st.code("\n".join(host_state.log_tail), language="text")
                else:
                    st.caption("Noch keine Tunnel-Logs verfügbar.")
                if host_state.stale_reason:
                    _show_admin_feedback("warning", "Host-Tunnel ist stale.", host_state.stale_reason)
                return

            with st.container(border=True):
                c1, c2 = st.columns([1.2, 1], vertical_alignment="bottom")
                with c1:
                    st.markdown("#### Status")
                    status = session.status if session else TunnelStatus.STOPPED
                    kind, message = _public_share_status_message(status)
                    if kind == "success":
                        _show_admin_feedback("success", message)
                    elif kind == "info":
                        _show_admin_feedback("info", message)
                    elif kind == "warning":
                        _show_admin_feedback("warning", message)
                    elif kind == "error":
                        _show_admin_feedback("error", message)
                    else:
                        st.caption(message)

                with c2:
                    is_running = bool(session and session.status == TunnelStatus.RUNNING)
                    if st.button(
                        "Freigabe starten",
                        type="primary",
                        use_container_width=True,
                        disabled=is_running,
                    ):
                        with st.spinner("Starte Cloudflare Quick Tunnel ..."):
                            started = manager.start(settings.public_share.local_url)
                            if started.status == TunnelStatus.RUNNING:
                                _show_admin_feedback("success", "Freigabe aktiv.")
                            else:
                                _show_admin_feedback("error", started.error_message or "Tunnelstart fehlgeschlagen.")
                        st.rerun()

                    if st.button(
                        "Freigabe stoppen",
                        use_container_width=True,
                        disabled=not bool(session),
                    ):
                        manager.stop()
                        _show_admin_feedback("success", "Freigabe gestoppt.")
                        st.rerun()

            diagnostics_left, diagnostics_right = st.columns(2)
            with diagnostics_left:
                st.text_input("Lokale Ziel-URL", value=settings.public_share.local_url, disabled=True)
                st.text_input("Provider", value=settings.public_share.provider, disabled=True)
                started_at = (
                    session.started_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                    if session
                    else "-"
                )
                st.text_input("Startzeit", value=started_at, disabled=True)
            with diagnostics_right:
                public_url_value = session.public_url if session and session.public_url else "-"
                st.text_input("Öffentliche URL", value=public_url_value, disabled=True)
                st.caption("Tipp: Feld markieren und kopieren (Strg/Cmd+C).")
                if session:
                    grace_active = bool(session.startup_grace_until and session.startup_grace_until > datetime.now(timezone.utc))
                    st.text_input(
                        "Lokale App gesund",
                        value="Ja" if session.last_local_healthcheck_ok is True else ("Nein" if session.last_local_healthcheck_ok is False else "Unbekannt"),
                        disabled=True,
                    )
                    st.text_input(
                        "Tunnelprozess lebt",
                        value="Ja" if session.last_process_alive is True else ("Nein" if session.last_process_alive is False else "Unbekannt"),
                        disabled=True,
                    )
                    st.text_input(
                        "Öffentliche URL erreichbar",
                        value="Ja" if session.last_public_healthcheck_ok is True else ("Nein" if session.last_public_healthcheck_ok is False else "Unbekannt"),
                        disabled=True,
                    )
                    st.text_input(
                        "Tunnelprozess Exit-Code",
                        value=str(session.last_exit_code) if session.last_exit_code is not None else "-",
                        disabled=True,
                    )
                    st.text_input(
                        "Public-Check Hard-Failure",
                        value="Ja" if session.last_public_check_hard_failure is True else ("Nein" if session.last_public_check_hard_failure is False else "Unbekannt"),
                        disabled=True,
                    )
                    st.text_input(
                        "Public-Check Failure-Counter",
                        value=str(session.public_check_failure_count),
                        disabled=True,
                    )
                    st.text_input(
                        "Letzter Public-Check-Typ",
                        value=session.last_public_check_type or "-",
                        disabled=True,
                    )
                    st.text_input(
                        "Letzter Public-Check-Fehler",
                        value=session.last_public_check_error or "-",
                        disabled=True,
                    )
                    st.text_input("Grace aktiv", value="Ja" if grace_active else "Nein", disabled=True)
                    st.text_input("Session stale", value="Ja" if session.status == TunnelStatus.STALE else "Nein", disabled=True)
                    st.text_input("stale_reason", value=session.stale_reason or "-", disabled=True)
                    st.text_input("error_message", value=session.error_message or "-", disabled=True)

                # Erweiterte Diagnostik: cloudflared Binary
                if isinstance(provider, CloudflareQuickTunnelProvider):
                    binary_diags = provider.get_binary_diagnostics()
                    st.text_input(
                        "cloudflared Binary (konfiguriert)",
                        value=binary_diags.get("configured_bin", "-"),
                        disabled=True,
                    )
                    st.text_input(
                        "Binary gefunden unter",
                        value=binary_diags.get("resolved_bin_path") or "NICHT GEFUNDEN",
                        disabled=True,
                    )
                    st.text_input(
                        "cloudflared Extra-Args",
                        value=" ".join(settings.public_share.cloudflared_extra_args) or "-",
                        disabled=True,
                    )
                    if binary_diags.get("version"):
                        st.text_input(
                            "cloudflared Version",
                            value=binary_diags["version"],
                            disabled=True,
                        )
                    else:
                        st.caption("⚠️ cloudflared-Version konnte nicht abgefragt werden")
                else:
                    st.text_input(
                        "cloudflared Binärdatei",
                        value=settings.public_share.cloudflared_bin,
                        disabled=True,
                    )
                    binary_available = provider.is_binary_available() if isinstance(provider, CloudflareQuickTunnelProvider) else False
                    st.text_input("Binärdatei gefunden", value="Ja" if binary_available else "Nein", disabled=True)

            can_open = bool(session and session.status == TunnelStatus.RUNNING and session.public_url)
            st.link_button(
                "Öffentliche URL öffnen",
                session.public_url if can_open and session and session.public_url else "http://localhost",
                disabled=not can_open,
                use_container_width=True,
            )

            st.markdown("##### Letzter Log-Ausschnitt")
            if session and session.raw_log_tail:
                st.code("\n".join(session.raw_log_tail[-15:]), language="text")
            else:
                st.caption("Noch keine Tunnel-Logs verfügbar.")

            if session and session.error_message:
                details = session.error_message
                level, message = _public_share_error_feedback(session)
                _show_admin_feedback(level, message, details)
            if session and session.stale_reason:
                _show_admin_feedback("warning", "Neue URL erforderlich.", session.stale_reason)
