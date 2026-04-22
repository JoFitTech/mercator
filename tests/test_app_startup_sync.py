from __future__ import annotations

from types import SimpleNamespace

from src.app import startup_sync


class _DbStatusDisconnected:
    class _MySql:
        is_connected = False
        active_target = None

    mysql = _MySql()


class _DummyMysqlSettings:
    mysql_sync_enabled = True
    mysql_startup_sync_enabled = True
    mysql_startup_sync_stale_minutes = 15
    mysql_active_target = "local"

    def get_mysql_target(self, target: str):  # noqa: ARG002
        return object()


def test_handle_startup_sync_skips_without_mysql_connection(monkeypatch) -> None:
    monkeypatch.setattr(startup_sync.st, "session_state", {})
    settings = SimpleNamespace(mysql=_DummyMysqlSettings())

    out = startup_sync.handle_startup_sync(
        settings=settings,
        db_status=_DbStatusDisconnected(),
        mysql_res=None,
    )

    assert out is not None
    assert out.skipped is True
    assert out.success is False
    assert out.error == "mysql_not_connected"


def test_render_startup_sync_shows_warning_for_skipped_failure(monkeypatch) -> None:
    captured: list[str] = []

    monkeypatch.setattr(startup_sync.st, "warning", lambda msg: captured.append(msg))
    monkeypatch.setattr(startup_sync.st, "toast", lambda msg: None)
    monkeypatch.setattr(startup_sync.st, "session_state", {})

    payload = startup_sync.StartupSyncOutcome(
        executed=False,
        skipped=True,
        marked_pending=False,
        success=False,
        message="Startup-Sync uebersprungen",
        error="repo_down",
    )

    startup_sync.render_startup_sync_toast_or_banner(payload)

    assert captured
    assert "repo_down" in captured[0]

