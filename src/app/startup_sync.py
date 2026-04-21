"""App-Hook fuer einmalige Startup-Sync-Ausfuehrung pro Session."""

from __future__ import annotations

import streamlit as st

from src.config.settings import AppSettings
from src.db.mysql_client import MySqlClient
from src.db.mysql_target_resolver import MySqlResolutionResult
from src.db.repositories.sync_state_repository import SyncStateRepository
from src.services.database_status_service import DatabaseStatus
from src.services.mysql_sync_service import MySqlSyncService
from src.services.startup_sync_service import StartupSyncOutcome, StartupSyncService
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)


def handle_startup_sync(
    settings: AppSettings,
    db_status: DatabaseStatus,
    mysql_res: MySqlResolutionResult | None,
) -> StartupSyncOutcome | None:
    if st.session_state.get("_startup_sync_checked"):
        return None
    st.session_state["_startup_sync_checked"] = True

    if not settings.mysql.mysql_sync_enabled:
        return None

    local_client = MySqlClient(settings.mysql.get_mysql_target("local"))
    uni_client = MySqlClient(settings.mysql.get_mysql_target("uni"))
    repo = SyncStateRepository(local_client)
    sync_service = MySqlSyncService()

    service = StartupSyncService(
        local_client=local_client,
        uni_client=uni_client,
        sync_state_repo=repo,
        sync_service=sync_service,
        startup_sync_enabled=settings.mysql.mysql_startup_sync_enabled,
        stale_minutes=settings.mysql.mysql_startup_sync_stale_minutes,
    )

    requested_target = mysql_res.requested_target if mysql_res else settings.mysql.mysql_active_target
    active_target = db_status.mysql.active_target if db_status else None
    outcome = service.run_for_start(
        requested_target=requested_target,
        active_target=active_target,
        uni_reachable=bool(active_target == "uni" and db_status.mysql.is_connected),
    )
    st.session_state["_startup_sync_outcome"] = outcome
    return outcome


def render_startup_sync_toast_or_banner(outcome: StartupSyncOutcome | None) -> None:
    payload = outcome or st.session_state.pop("_startup_sync_outcome", None)
    if payload is None:
        return

    if payload.executed and payload.success:
        st.toast("Startup-Sync local -> uni erfolgreich ausgeführt.")
    elif payload.executed and not payload.success:
        st.warning(f"Startup-Sync fehlgeschlagen: {payload.error or payload.message}")
    elif payload.marked_pending:
        LOGGER.info("startup_sync pending marker set for next uni-start")
