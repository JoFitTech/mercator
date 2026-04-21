"""Repository fuer den persistenten Startup-MySQL-Sync-Status."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.db.mysql_client import MySqlClient


@dataclass(slots=True)
class StartupSyncState:
    state_key: str
    pending_uni_sync: bool
    sync_in_progress: bool
    last_start_mode: str | None
    last_requested_target: str | None
    last_active_target: str | None
    last_sync_direction: str | None
    last_sync_status: str | None
    last_sync_error: str | None
    last_sync_started_at: datetime | None
    last_sync_finished_at: datetime | None
    last_successful_uni_sync_at: datetime | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SyncStateRepository:
    """Persistiert den Startup-Sync-Zustand in ``app_sync_state``."""

    STATE_KEY = "startup_mysql_sync"

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _as_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "y"}

    def _row_to_state(self, row: dict) -> StartupSyncState:
        return StartupSyncState(
            state_key=str(row.get("state_key") or self.STATE_KEY),
            pending_uni_sync=self._as_bool(row.get("pending_uni_sync")),
            sync_in_progress=self._as_bool(row.get("sync_in_progress")),
            last_start_mode=row.get("last_start_mode"),
            last_requested_target=row.get("last_requested_target"),
            last_active_target=row.get("last_active_target"),
            last_sync_direction=row.get("last_sync_direction"),
            last_sync_status=row.get("last_sync_status"),
            last_sync_error=row.get("last_sync_error"),
            last_sync_started_at=row.get("last_sync_started_at"),
            last_sync_finished_at=row.get("last_sync_finished_at"),
            last_successful_uni_sync_at=row.get("last_successful_uni_sync_at"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def create_default_if_missing(self) -> StartupSyncState:
        sql = """
            INSERT IGNORE INTO app_sync_state (state_key, pending_uni_sync, sync_in_progress)
            VALUES (%s, FALSE, FALSE)
        """
        with self._client.connection(include_database=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (self.STATE_KEY,))
            conn.commit()
        return self.load()

    def load(self) -> StartupSyncState:
        query = "SELECT * FROM app_sync_state WHERE state_key = %s LIMIT 1"
        with self._client.connection(include_database=True) as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(query, (self.STATE_KEY,))
                row = cursor.fetchone()
        if row is None:
            return self.create_default_if_missing()
        return self._row_to_state(row)

    def upsert(self, state: StartupSyncState) -> None:
        sql = """
            INSERT INTO app_sync_state (
                state_key, pending_uni_sync, sync_in_progress,
                last_start_mode, last_requested_target, last_active_target,
                last_sync_direction, last_sync_status, last_sync_error,
                last_sync_started_at, last_sync_finished_at, last_successful_uni_sync_at
            ) VALUES (
                %(state_key)s, %(pending_uni_sync)s, %(sync_in_progress)s,
                %(last_start_mode)s, %(last_requested_target)s, %(last_active_target)s,
                %(last_sync_direction)s, %(last_sync_status)s, %(last_sync_error)s,
                %(last_sync_started_at)s, %(last_sync_finished_at)s, %(last_successful_uni_sync_at)s
            )
            ON DUPLICATE KEY UPDATE
                pending_uni_sync = VALUES(pending_uni_sync),
                sync_in_progress = VALUES(sync_in_progress),
                last_start_mode = VALUES(last_start_mode),
                last_requested_target = VALUES(last_requested_target),
                last_active_target = VALUES(last_active_target),
                last_sync_direction = VALUES(last_sync_direction),
                last_sync_status = VALUES(last_sync_status),
                last_sync_error = VALUES(last_sync_error),
                last_sync_started_at = VALUES(last_sync_started_at),
                last_sync_finished_at = VALUES(last_sync_finished_at),
                last_successful_uni_sync_at = VALUES(last_successful_uni_sync_at)
        """
        params = {
            "state_key": state.state_key,
            "pending_uni_sync": state.pending_uni_sync,
            "sync_in_progress": state.sync_in_progress,
            "last_start_mode": state.last_start_mode,
            "last_requested_target": state.last_requested_target,
            "last_active_target": state.last_active_target,
            "last_sync_direction": state.last_sync_direction,
            "last_sync_status": state.last_sync_status,
            "last_sync_error": state.last_sync_error,
            "last_sync_started_at": state.last_sync_started_at,
            "last_sync_finished_at": state.last_sync_finished_at,
            "last_successful_uni_sync_at": state.last_successful_uni_sync_at,
        }
        with self._client.connection(include_database=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
            conn.commit()

    def mark_pending_due_to_non_uni_start(self, requested_target: str, active_target: str | None, start_mode: str) -> StartupSyncState:
        state = self.load()
        state.pending_uni_sync = True
        state.last_start_mode = start_mode
        state.last_requested_target = requested_target
        state.last_active_target = active_target
        state.last_sync_status = "SKIPPED_PENDING_MARKED"
        state.sync_in_progress = False
        self.upsert(state)
        return state

    def mark_start(self, requested_target: str, active_target: str | None, start_mode: str, status: str) -> StartupSyncState:
        state = self.load()
        state.last_start_mode = start_mode
        state.last_requested_target = requested_target
        state.last_active_target = active_target
        state.last_sync_status = status
        self.upsert(state)
        return state

    def mark_sync_running(self, direction: str) -> StartupSyncState:
        now = datetime.now(timezone.utc)
        state = self.load()
        state.sync_in_progress = True
        state.last_sync_direction = direction
        state.last_sync_status = "RUNNING"
        state.last_sync_error = None
        state.last_sync_started_at = now
        self.upsert(state)
        return state

    def mark_sync_success(self, direction: str) -> StartupSyncState:
        now = datetime.now(timezone.utc)
        state = self.load()
        state.pending_uni_sync = False
        state.sync_in_progress = False
        state.last_sync_direction = direction
        state.last_sync_status = "SUCCESS"
        state.last_sync_error = None
        state.last_sync_finished_at = now
        state.last_successful_uni_sync_at = now
        self.upsert(state)
        return state

    def mark_sync_failed(self, direction: str, error: str, status: str = "FAILED") -> StartupSyncState:
        now = datetime.now(timezone.utc)
        state = self.load()
        state.pending_uni_sync = True
        state.sync_in_progress = False
        state.last_sync_direction = direction
        state.last_sync_status = status
        state.last_sync_error = error
        state.last_sync_finished_at = now
        self.upsert(state)
        return state

    def clear_stale_lock_if_needed(self, stale_minutes: int) -> bool:
        state = self.load()
        if not state.sync_in_progress or state.last_sync_started_at is None:
            return False

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(1, stale_minutes))
        started = state.last_sync_started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if started >= cutoff:
            return False

        self.mark_sync_failed(
            direction=state.last_sync_direction or "local_to_uni",
            error="Startup sync lock recovered after stale RUNNING state.",
            status="FAILED_STALE_RECOVERED",
        )
        return True
