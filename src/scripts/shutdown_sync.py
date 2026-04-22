"""Shutdown-Sync-Skript: Synchronisiert local -> uni beim App-Stop.

Aufruf:
    python -m src.scripts.shutdown_sync

Exit-Codes:
    0  Sync erfolgreich oder nicht benötigt
    1  Sync fehlgeschlagen (uni nicht erreichbar o.ä.)
    2  Konfigurationsfehler
"""

from __future__ import annotations

import sys

from src.config.settings import load_settings
from src.db.mysql_client import MySqlClient
from src.db.repositories.sync_state_repository import SyncStateRepository
from src.services.mysql_sync_service import MySqlSyncService
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)


def _test_connection(client: MySqlClient, label: str) -> bool:
    """Prüft ob eine MySQL-Verbindung aufgebaut werden kann."""
    try:
        with client.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception as exc:
        LOGGER.warning("shutdown_sync: %s nicht erreichbar – %s", label, exc)
        return False


def run_shutdown_sync() -> int:
    """Führt den Shutdown-Sync durch. Gibt Exit-Code zurück."""
    print("⏳ Shutdown-Sync wird vorbereitet...", flush=True)

    try:
        settings = load_settings()
    except Exception as exc:
        print(f"❌ Einstellungen konnten nicht geladen werden: {exc}", file=sys.stderr)
        return 2

    if not settings.mysql.mysql_sync_enabled:
        print("ℹ️  MySQL-Sync ist deaktiviert (MYSQL_SYNC_ENABLED=false). Überspringe.", flush=True)
        return 0

    try:
        local_client = MySqlClient(settings.mysql.get_mysql_target("local"))
        uni_client = MySqlClient(settings.mysql.get_mysql_target("uni"))
    except Exception as exc:
        print(f"❌ MySQL-Clients konnten nicht erstellt werden: {exc}", file=sys.stderr)
        return 2

    # Verbindungsprüfung
    print("🔍 Prüfe lokale MySQL...", flush=True)
    if not _test_connection(local_client, "local MySQL"):
        print("⚠️  Lokale MySQL nicht erreichbar. Shutdown-Sync übersprungen.", flush=True)
        return 0  # Kein Fehler – DB war schon nicht da

    print("🔍 Prüfe Uni-MySQL...", flush=True)
    if not _test_connection(uni_client, "uni MySQL"):
        print("⚠️  Uni-MySQL nicht erreichbar. Shutdown-Sync übersprungen.", flush=True)
        # Pending markieren damit nächster Start den Sync nachholt
        try:
            repo = SyncStateRepository(local_client)
            repo.mark_pending_due_to_non_uni_start(
                requested_target="uni",
                active_target="local",
                start_mode="SHUTDOWN_NO_UNI",
            )
            print("📌 Pending-Sync-Flag gesetzt für nächsten Start.", flush=True)
        except Exception as exc:
            LOGGER.warning("shutdown_sync: Pending-Flag konnte nicht gesetzt werden: %s", exc)
        return 0

    # Sync durchführen
    print("🔄 Starte Shutdown-Sync local → uni ...", flush=True)
    sync_service = MySqlSyncService()
    try:
        repo = SyncStateRepository(local_client)
        repo.mark_sync_running(direction="local_to_uni")
    except Exception as exc:
        LOGGER.warning("shutdown_sync: State-Repo nicht verfügbar: %s", exc)

    try:
        summary = sync_service.sync_startup_reconnect(
            local_client=local_client,
            uni_client=uni_client,
        )
        companies_written = summary.company_result.written_count
        trades_written = summary.insider_trade_result.written_count
        settings_written = (
            (summary.app_filter_settings_result.written_count if summary.app_filter_settings_result else 0)
            + (summary.app_runtime_preferences_result.written_count if summary.app_runtime_preferences_result else 0)
        )
        print(
            f"✅ Shutdown-Sync erfolgreich! "
            f"Companies: {companies_written}, Trades: {trades_written}, Settings: {settings_written}",
            flush=True,
        )
        try:
            repo = SyncStateRepository(local_client)
            repo.mark_sync_success(direction="local_to_uni")
        except Exception:
            pass
        return 0
    except Exception as exc:
        print(f"❌ Shutdown-Sync fehlgeschlagen: {exc}", file=sys.stderr)
        try:
            repo = SyncStateRepository(local_client)
            repo.mark_sync_failed(direction="local_to_uni", error=str(exc))
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(run_shutdown_sync())

