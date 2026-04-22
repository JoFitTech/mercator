"""Orchestrator fuer kontrollierten Startup-Reconnect-Sync (local -> uni)."""

from __future__ import annotations

from dataclasses import dataclass

from src.db.mysql_client import MySqlClient
from src.db.repositories.sync_state_repository import SyncStateRepository
from src.services.mysql_sync_service import MySqlSyncService
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)


@dataclass(slots=True)
class StartupSyncOutcome:
    executed: bool
    skipped: bool
    marked_pending: bool
    success: bool
    message: str
    error: str | None = None
    direction: str | None = None


class StartupSyncService:
    """Führt die Startup-Entscheidung und ggf. den Reconnect-Sync aus."""

    def __init__(
        self,
        local_client: MySqlClient,
        uni_client: MySqlClient,
        sync_state_repo: SyncStateRepository,
        sync_service: MySqlSyncService,
        startup_sync_enabled: bool,
        stale_minutes: int = 15,
    ) -> None:
        self._local_client = local_client
        self._uni_client = uni_client
        self._sync_state_repo = sync_state_repo
        self._sync_service = sync_service
        self._startup_sync_enabled = startup_sync_enabled
        self._stale_minutes = stale_minutes

    def run_for_start(
        self,
        requested_target: str,
        active_target: str | None,
        uni_reachable: bool,
    ) -> StartupSyncOutcome:
        LOGGER.info(
            "startup_sync evaluate requested=%s active=%s uni_reachable=%s",
            requested_target,
            active_target,
            uni_reachable,
        )
        if not self._startup_sync_enabled:
            return StartupSyncOutcome(
                executed=False,
                skipped=True,
                marked_pending=False,
                success=True,
                message="Startup-Sync deaktiviert.",
            )

        repo_available = True
        repo_error: str | None = None
        try:
            stale_recovered = self._sync_state_repo.clear_stale_lock_if_needed(self._stale_minutes)
            if stale_recovered:
                LOGGER.warning("startup_sync stale_lock_recovered")
        except Exception as exc:
            repo_available = False
            repo_error = str(exc)
            LOGGER.warning("startup_sync state_repo_unavailable stage=stale_check error=%s", repo_error)

        normalized_requested = (requested_target or "").strip().lower()
        normalized_active = (active_target or "").strip().lower() if active_target else None

        if normalized_active != "uni":
            start_mode = "FALLBACK_LOCAL" if normalized_requested == "uni" and normalized_active == "local" else "LOCAL"
            if repo_available:
                try:
                    self._sync_state_repo.mark_pending_due_to_non_uni_start(
                        requested_target=normalized_requested or "local",
                        active_target=normalized_active,
                        start_mode=start_mode,
                    )
                except Exception as exc:
                    repo_available = False
                    repo_error = str(exc)
                    LOGGER.warning("startup_sync state_repo_unavailable stage=mark_pending error=%s", repo_error)
            LOGGER.info(
                "startup_sync mark_pending reason=active_target_not_uni requested=%s active=%s",
                normalized_requested,
                normalized_active,
            )
            return StartupSyncOutcome(
                executed=False,
                skipped=True,
                marked_pending=repo_available,
                success=repo_available,
                message=(
                    "Uni-MySQL beim Start nicht aktiv; Pending-Sync markiert."
                    if repo_available
                    else "Uni-MySQL beim Start nicht aktiv, Pending-Sync konnte nicht persistiert werden."
                ),
                error=repo_error,
            )

        pending_uni_sync = True
        if repo_available:
            try:
                state = self._sync_state_repo.load()
                pending_uni_sync = bool(state.pending_uni_sync)
                if not pending_uni_sync:
                    self._sync_state_repo.mark_start(
                        requested_target=normalized_requested or "uni",
                        active_target="uni",
                        start_mode="UNI",
                        status="SKIPPED_NO_PENDING",
                    )
                    LOGGER.info("startup_sync skip reason=no_pending_sync")
                    return StartupSyncOutcome(
                        executed=False,
                        skipped=True,
                        marked_pending=False,
                        success=True,
                        message="Kein ausstehender Startup-Sync vorhanden.",
                    )
            except Exception as exc:
                repo_available = False
                repo_error = str(exc)
                LOGGER.warning("startup_sync state_repo_unavailable stage=load_or_mark_start error=%s", repo_error)
                # Fail-open: auf aktivem Uni-Start versuchen wir den Reconnect-Sync trotzdem best effort.
                pending_uni_sync = True

        if not uni_reachable:
            return StartupSyncOutcome(
                executed=False,
                skipped=True,
                marked_pending=repo_available and pending_uni_sync,
                success=False,
                message="Uni-MySQL nicht erreichbar, Pending bleibt gesetzt.",
                error=repo_error or "uni_not_reachable",
            )

        direction = "local_to_uni"
        if repo_available:
            try:
                self._sync_state_repo.mark_sync_running(direction=direction)
            except Exception as exc:
                repo_available = False
                repo_error = str(exc)
                LOGGER.warning("startup_sync state_repo_unavailable stage=mark_running error=%s", repo_error)
        LOGGER.info("startup_sync begin direction=%s", direction)

        try:
            summary = self._sync_service.sync_startup_reconnect(
                local_client=self._local_client,
                uni_client=self._uni_client,
            )
            if repo_available:
                try:
                    self._sync_state_repo.mark_sync_success(direction=direction)
                except Exception as exc:
                    repo_available = False
                    repo_error = str(exc)
                    LOGGER.warning("startup_sync state_repo_unavailable stage=mark_success error=%s", repo_error)
            LOGGER.info(
                "startup_sync success direction=%s companies_written=%s trades_written=%s settings_written=%s",
                direction,
                summary.company_result.written_count,
                summary.insider_trade_result.written_count,
                (summary.app_filter_settings_result.written_count if summary.app_filter_settings_result else 0)
                + (summary.app_runtime_preferences_result.written_count if summary.app_runtime_preferences_result else 0),
            )
            return StartupSyncOutcome(
                executed=True,
                skipped=False,
                marked_pending=False,
                success=True,
                message=(
                    "Startup-Reconnect-Sync erfolgreich."
                    if repo_available
                    else "Startup-Reconnect-Sync erfolgreich (State-Repo war nicht verfuegbar)."
                ),
                error=repo_error,
                direction=direction,
            )
        except Exception as exc:
            error = str(exc)
            if repo_available:
                try:
                    self._sync_state_repo.mark_sync_failed(direction=direction, error=error)
                except Exception as mark_exc:
                    LOGGER.warning(
                        "startup_sync state_repo_unavailable stage=mark_failed error=%s",
                        str(mark_exc),
                    )
            LOGGER.error("startup_sync failed direction=%s error=%s", direction, error)
            return StartupSyncOutcome(
                executed=True,
                skipped=False,
                marked_pending=True,
                success=False,
                message="Startup-Reconnect-Sync fehlgeschlagen.",
                error=f"{error}; state_repo={repo_error}" if repo_error else error,
                direction=direction,
            )
