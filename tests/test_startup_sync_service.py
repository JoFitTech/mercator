from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from src.db.repositories.sync_state_repository import StartupSyncState
from src.services.startup_sync_service import StartupSyncService


class _RepoStub:
    def __init__(self, state: StartupSyncState) -> None:
        self.state = state
        self.cleared_stale = False

    def load(self) -> StartupSyncState:
        return self.state

    def clear_stale_lock_if_needed(self, stale_minutes: int) -> bool:
        if self.state.sync_in_progress and self.state.last_sync_started_at:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
            if self.state.last_sync_started_at < cutoff:
                self.state.sync_in_progress = False
                self.state.last_sync_status = "FAILED_STALE_RECOVERED"
                self.cleared_stale = True
                return True
        return False

    def mark_pending_due_to_non_uni_start(self, requested_target: str, active_target: str | None, start_mode: str):
        self.state.pending_uni_sync = True
        self.state.last_requested_target = requested_target
        self.state.last_active_target = active_target
        self.state.last_start_mode = start_mode

    def mark_start(self, requested_target: str, active_target: str | None, start_mode: str, status: str):
        self.state.last_requested_target = requested_target
        self.state.last_active_target = active_target
        self.state.last_start_mode = start_mode
        self.state.last_sync_status = status

    def mark_sync_running(self, direction: str):
        self.state.sync_in_progress = True
        self.state.last_sync_direction = direction
        self.state.last_sync_status = "RUNNING"

    def mark_sync_success(self, direction: str):
        self.state.pending_uni_sync = False
        self.state.sync_in_progress = False
        self.state.last_sync_status = "SUCCESS"
        self.state.last_sync_direction = direction

    def mark_sync_failed(self, direction: str, error: str, status: str = "FAILED"):
        self.state.pending_uni_sync = True
        self.state.sync_in_progress = False
        self.state.last_sync_status = status
        self.state.last_sync_error = error
        self.state.last_sync_direction = direction


class _SyncServiceStub:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.called = False

    def sync_startup_reconnect(self, local_client, uni_client):  # noqa: ANN001
        self.called = True
        if self.should_fail:
            raise RuntimeError("boom")

        class _Res:
            class _R:
                written_count = 1

            company_result = _R()
            insider_trade_result = _R()
            app_filter_settings_result = _R()
            app_runtime_preferences_result = _R()

        return _Res()


class _BrokenRepoStub:
    def clear_stale_lock_if_needed(self, stale_minutes: int) -> bool:  # noqa: ARG002
        raise RuntimeError("repo down")

    def mark_pending_due_to_non_uni_start(self, requested_target: str, active_target: str | None, start_mode: str):  # noqa: ARG002
        raise RuntimeError("repo down")

    def load(self) -> StartupSyncState:
        raise RuntimeError("repo down")

    def mark_start(self, requested_target: str, active_target: str | None, start_mode: str, status: str):  # noqa: ARG002
        raise RuntimeError("repo down")

    def mark_sync_running(self, direction: str):  # noqa: ARG002
        raise RuntimeError("repo down")

    def mark_sync_success(self, direction: str):  # noqa: ARG002
        raise RuntimeError("repo down")

    def mark_sync_failed(self, direction: str, error: str, status: str = "FAILED"):  # noqa: ARG002
        raise RuntimeError("repo down")


def _base_state() -> StartupSyncState:
    return StartupSyncState(
        state_key="startup_mysql_sync",
        pending_uni_sync=False,
        sync_in_progress=False,
        last_start_mode=None,
        last_requested_target=None,
        last_active_target=None,
        last_sync_direction=None,
        last_sync_status=None,
        last_sync_error=None,
        last_sync_started_at=None,
        last_sync_finished_at=None,
        last_successful_uni_sync_at=None,
    )


def _service(repo: _RepoStub, sync_stub: _SyncServiceStub, enabled: bool = True) -> StartupSyncService:
    return StartupSyncService(
        local_client=object(),
        uni_client=object(),
        sync_state_repo=repo,
        sync_service=sync_stub,
        startup_sync_enabled=enabled,
        stale_minutes=15,
    )


def test_marks_pending_when_started_on_local() -> None:
    repo = _RepoStub(_base_state())
    svc = _service(repo, _SyncServiceStub())

    out = svc.run_for_start(requested_target="local", active_target="local", uni_reachable=False)

    assert out.marked_pending is True
    assert repo.state.pending_uni_sync is True


def test_marks_fallback_local_mode_when_requested_uni_but_active_local() -> None:
    repo = _RepoStub(_base_state())
    svc = _service(repo, _SyncServiceStub())

    svc.run_for_start(requested_target="uni", active_target="local", uni_reachable=False)

    assert repo.state.last_start_mode == "FALLBACK_LOCAL"
    assert repo.state.pending_uni_sync is True


def test_skips_when_uni_and_no_pending() -> None:
    repo = _RepoStub(_base_state())
    sync_stub = _SyncServiceStub()
    svc = _service(repo, sync_stub)

    out = svc.run_for_start(requested_target="uni", active_target="uni", uni_reachable=True)

    assert out.skipped is True
    assert sync_stub.called is False
    assert repo.state.last_sync_status == "SKIPPED_NO_PENDING"


def test_executes_sync_when_uni_and_pending() -> None:
    repo = _RepoStub(replace(_base_state(), pending_uni_sync=True))
    sync_stub = _SyncServiceStub()
    svc = _service(repo, sync_stub)

    out = svc.run_for_start(requested_target="uni", active_target="uni", uni_reachable=True)

    assert out.executed is True
    assert out.success is True
    assert sync_stub.called is True
    assert repo.state.pending_uni_sync is False


def test_failed_sync_keeps_pending_true() -> None:
    repo = _RepoStub(replace(_base_state(), pending_uni_sync=True))
    sync_stub = _SyncServiceStub(should_fail=True)
    svc = _service(repo, sync_stub)

    out = svc.run_for_start(requested_target="uni", active_target="uni", uni_reachable=True)

    assert out.success is False
    assert repo.state.pending_uni_sync is True
    assert repo.state.sync_in_progress is False
    assert repo.state.last_sync_status == "FAILED"


def test_stale_lock_gets_cleared() -> None:
    stale_state = replace(
        _base_state(),
        pending_uni_sync=True,
        sync_in_progress=True,
        last_sync_started_at=datetime.now(timezone.utc) - timedelta(minutes=45),
    )
    repo = _RepoStub(stale_state)
    svc = _service(repo, _SyncServiceStub())

    svc.run_for_start(requested_target="uni", active_target="uni", uni_reachable=True)

    assert repo.cleared_stale is True


def test_disabled_startup_sync_is_skipped() -> None:
    repo = _RepoStub(replace(_base_state(), pending_uni_sync=True))
    sync_stub = _SyncServiceStub()
    svc = _service(repo, sync_stub, enabled=False)

    out = svc.run_for_start(requested_target="uni", active_target="uni", uni_reachable=True)

    assert out.skipped is True
    assert sync_stub.called is False


def test_repo_failure_on_uni_start_uses_best_effort_sync_without_crash() -> None:
    sync_stub = _SyncServiceStub()
    svc = _service(_BrokenRepoStub(), sync_stub)

    out = svc.run_for_start(requested_target="uni", active_target="uni", uni_reachable=True)

    assert out.executed is True
    assert out.success is True
    assert sync_stub.called is True
    assert "State-Repo" in out.message


def test_repo_failure_on_local_start_skips_with_error_instead_of_crash() -> None:
    sync_stub = _SyncServiceStub()
    svc = _service(_BrokenRepoStub(), sync_stub)

    out = svc.run_for_start(requested_target="local", active_target="local", uni_reachable=False)

    assert out.skipped is True
    assert out.success is False
    assert out.marked_pending is False
    assert sync_stub.called is False

