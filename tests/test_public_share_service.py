from __future__ import annotations

from datetime import datetime, timezone
import io
from pathlib import Path
from queue import Queue
from urllib import error as url_error

from src.services.public_share_service import (
    CloudflareQuickTunnelProvider,
    TunnelManager,
    TunnelSession,
    TunnelStatus,
    sync_public_share_sidebar_state,
)


class _ProviderStub:
    def __init__(self, session: TunnelSession):
        self.session = session
        self.start_calls = 0
        self.stop_calls = 0

    def start(self, local_url: str) -> TunnelSession:
        self.start_calls += 1
        self.session.local_url = local_url
        return self.session

    def stop(self, session: TunnelSession) -> None:
        self.stop_calls += 1

    def get_status(self, session: TunnelSession) -> TunnelStatus:
        return session.status


class _FakeStdout:
    def __init__(self, lines: list[str]):
        self._lines = lines

    def __iter__(self):
        return iter(self._lines)


class _FakeProcess:
    def __init__(self, lines: list[str], poll_value=None, pid: int = 321):
        self.stdout = _FakeStdout(lines)
        self._poll_value = poll_value
        self.pid = pid
        self.terminated = False

    def poll(self):
        return self._poll_value

    def terminate(self) -> None:
        self.terminated = True
        self._poll_value = 0

    def wait(self, timeout: float | None = None) -> int:
        return 0

    def kill(self) -> None:
        self._poll_value = 1


def _build_session(status: TunnelStatus = TunnelStatus.RUNNING) -> TunnelSession:
    return TunnelSession(
        provider="cloudflare",
        local_url="http://localhost:8501",
        public_url="https://demo.trycloudflare.com",
        pid=22,
        started_at=datetime.now(timezone.utc),
        status=status,
        raw_log_tail=[],
    )


def test_extract_public_url_from_cloudflared_log_line() -> None:
    line = "INF + Generated quick Tunnel URL: https://demo-name.trycloudflare.com"
    parsed = CloudflareQuickTunnelProvider.extract_public_url_from_log_line(line)
    assert parsed == "https://demo-name.trycloudflare.com"


def test_missing_binary_returns_error_session() -> None:
    provider = CloudflareQuickTunnelProvider(cloudflared_bin="definitely_missing_cloudflared_bin")

    session = provider.start("http://localhost:8501")

    assert session.status == TunnelStatus.ERROR
    assert session.pid is None
    assert "cloudflared" in (session.error_message or "")


def test_get_binary_diagnostics_when_binary_not_found() -> None:
    provider = CloudflareQuickTunnelProvider(cloudflared_bin="definitely_missing_cloudflared_bin")

    diags = provider.get_binary_diagnostics()

    assert diags["binary_available"] == "Nein"
    assert diags["resolved_bin_path"] is None
    assert diags["configured_bin"] == "definitely_missing_cloudflared_bin"


def test_prestart_check_rejects_unreachable_local_url(monkeypatch) -> None:
    provider = CloudflareQuickTunnelProvider(cloudflared_bin="cloudflared")

    # Fake binary available
    monkeypatch.setattr(provider, "is_binary_available", lambda: True)
    monkeypatch.setattr(provider, "_resolve_bin", lambda: "cloudflared")
    # Fake local URL not healthy
    monkeypatch.setattr(provider, "_is_local_url_healthy", lambda _url: False)

    session = provider.start("http://localhost:8501")

    assert session.status == TunnelStatus.ERROR
    assert "Vorstart-Fehler" in (session.error_message or "")
    assert "nicht erreichbar" in (session.error_message or "").lower()


def test_resolve_bin_prefers_repo_local_cloudflared_exe_when_not_in_path(monkeypatch, tmp_path) -> None:
    provider = CloudflareQuickTunnelProvider(cloudflared_bin="cloudflared")
    fake_repo_root = tmp_path / "repo"
    fake_repo_root.mkdir()
    fake_exe = fake_repo_root / "cloudflared.exe"
    fake_exe.write_text("binary")

    monkeypatch.setattr("shutil.which", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
    monkeypatch.setattr(
        CloudflareQuickTunnelProvider,
        "_is_executable_file",
        staticmethod(lambda path: path == fake_exe),
    )
    monkeypatch.setattr(
        "src.services.public_share_service.Path.resolve",
        lambda self: fake_repo_root / "src" / "services" / "public_share_service.py",
    )

    resolved = provider._resolve_bin()

    assert resolved == str(fake_exe)


def test_output_reader_enqueues_all_lines() -> None:
    queue: Queue[str | None] = Queue()
    process = _FakeProcess(lines=["line 1\n", "line 2\n"], poll_value=0)

    CloudflareQuickTunnelProvider._enqueue_output(process, queue)

    assert queue.get() == "line 1\n"
    assert queue.get() == "line 2\n"
    assert queue.get() is None


def test_start_reads_url_from_threaded_output(monkeypatch) -> None:
    provider = CloudflareQuickTunnelProvider(cloudflared_bin="cloudflared", startup_timeout_seconds=1)
    fake_process = _FakeProcess(
        lines=["Booting cloudflared\n", "URL is https://abc.trycloudflare.com\n"],
        poll_value=None,
        pid=777,
    )

    monkeypatch.setattr(provider, "is_binary_available", lambda: True)
    monkeypatch.setattr(provider, "_resolve_bin", lambda: "cloudflared")
    monkeypatch.setattr(provider, "_is_local_url_healthy", lambda _url: True)
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: fake_process)

    session = provider.start("http://localhost:8501")

    assert session.status == TunnelStatus.RUNNING
    assert session.public_url == "https://abc.trycloudflare.com"
    assert session.pid == 777
    assert "Booting cloudflared" in session.raw_log_tail[0]


def test_start_timeout_without_url_terminates_process(monkeypatch) -> None:
    provider = CloudflareQuickTunnelProvider(cloudflared_bin="cloudflared", startup_timeout_seconds=0)
    fake_process = _FakeProcess(lines=["still booting\n"], poll_value=None)

    monkeypatch.setattr(provider, "is_binary_available", lambda: True)
    monkeypatch.setattr(provider, "_resolve_bin", lambda: "cloudflared")
    monkeypatch.setattr(provider, "_is_local_url_healthy", lambda _url: True)
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: fake_process)

    session = provider.start("http://localhost:8501")

    assert session.status == TunnelStatus.ERROR
    assert "keine öffentliche URL" in (session.error_message or "")
    assert fake_process.terminated is True


def test_get_status_transitions_to_stale_when_process_died() -> None:
    class _DeadProcess:
        def poll(self):
            return 1

    provider = CloudflareQuickTunnelProvider()
    session = _build_session()
    session.process = _DeadProcess()  # type: ignore[assignment]

    status = provider.get_status(session)

    assert status == TunnelStatus.STALE


def test_get_status_reports_warning_when_url_unreachable() -> None:
    provider = CloudflareQuickTunnelProvider()
    session = _build_session()

    class _AliveProcess:
        def poll(self):
            return None

    session.process = _AliveProcess()  # type: ignore[assignment]

    provider._is_local_url_healthy = lambda _: False  # type: ignore[method-assign]
    provider._is_public_url_reachable = lambda _: True  # type: ignore[method-assign]
    status = provider.get_status(session)

    assert status == TunnelStatus.WARNING
    assert session.last_healthcheck_ok is False


def test_get_status_reports_running_when_local_url_healthy() -> None:
    provider = CloudflareQuickTunnelProvider()
    session = _build_session(status=TunnelStatus.RUNNING)
    session.process = None
    session.last_healthcheck_at = None

    class _AliveProcess:
        def poll(self):
            return None

    session.process = _AliveProcess()  # type: ignore[assignment]

    provider._is_local_url_healthy = lambda _: True  # type: ignore[method-assign]
    provider._is_public_url_reachable = lambda _: True  # type: ignore[method-assign]
    status = provider.get_status(session)

    assert status == TunnelStatus.RUNNING
    assert session.last_healthcheck_ok is True
    assert session.error_message is None


def test_get_status_marks_stale_when_public_url_dead_but_local_healthy() -> None:
    provider = CloudflareQuickTunnelProvider()
    session = _build_session(status=TunnelStatus.RUNNING)

    class _AliveProcess:
        def poll(self):
            return None

    session.process = _AliveProcess()  # type: ignore[assignment]
    provider._is_local_url_healthy = lambda _: True  # type: ignore[method-assign]
    provider._last_public_url_error = "Öffentliche URL ist nicht erreichbar."
    provider._is_public_url_reachable = lambda _: False  # type: ignore[method-assign]

    status = provider.get_status(session)

    assert status == TunnelStatus.STALE
    assert session.last_local_healthcheck_ok is True
    assert session.last_public_healthcheck_ok is False
    assert "Öffentliche URL" in (session.error_message or "")


def test_get_status_detects_cloudflare_1033_as_stale(monkeypatch) -> None:
    provider = CloudflareQuickTunnelProvider(healthcheck_timeout_seconds=0.1)

    def _raise_http_error(*_args, **_kwargs):
        raise url_error.HTTPError(  # type: ignore[call-arg]
            url="https://demo.trycloudflare.com",
            code=530,
            msg="Origin DNS error",
            hdrs=None,
            fp=io.BytesIO(b"<html>Cloudflare Error 1033</html>"),
        )

    monkeypatch.setattr("src.services.public_share_service.url_request.urlopen", _raise_http_error)
    ok, message = provider._check_public_url("https://demo.trycloudflare.com")

    assert ok is False
    assert message is not None
    assert "1033" in message


def test_manager_marks_stale_if_process_missing_but_pid_is_dead(monkeypatch) -> None:
    session = _build_session(status=TunnelStatus.RUNNING)
    session.process = None
    session.pid = 999999
    provider = _ProviderStub(session)
    manager = TunnelManager(provider=provider, provider_name="cloudflare", default_local_url="http://localhost:8501")
    manager.session = session

    def _raise_process_lookup(pid: int, sig: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr("os.kill", _raise_process_lookup)

    result = manager.get_session()

    assert result is not None
    assert result.status == TunnelStatus.STALE
    assert result.stale_reason is not None


def test_manager_with_real_provider_keeps_stale_when_pid_is_dead_and_public_url_exists(monkeypatch) -> None:
    provider = CloudflareQuickTunnelProvider()
    session = _build_session(status=TunnelStatus.RUNNING)
    session.process = None
    session.pid = 999999
    manager = TunnelManager(provider=provider, provider_name="cloudflare", default_local_url="http://localhost:8501")
    manager.session = session

    def _raise_process_lookup(pid: int, sig: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr("os.kill", _raise_process_lookup)
    monkeypatch.setattr(provider, "_is_public_url_reachable", lambda _url: True)

    result = manager.get_session()

    assert result is not None
    assert result.status == TunnelStatus.STALE
    assert result.stale_reason is not None


def test_real_provider_stale_session_stays_stale() -> None:
    provider = CloudflareQuickTunnelProvider()
    session = _build_session(status=TunnelStatus.STALE)
    session.process = None
    session.pid = None

    status = provider.get_status(session)

    assert status == TunnelStatus.STALE


def test_real_provider_reachability_true_does_not_reactivate_stale_session(monkeypatch) -> None:
    provider = CloudflareQuickTunnelProvider()
    session = _build_session(status=TunnelStatus.STALE)
    session.process = None
    session.pid = None

    monkeypatch.setattr(provider, "_is_public_url_reachable", lambda _url: True)

    status = provider.get_status(session)

    assert status == TunnelStatus.STALE


def test_stop_logic_sets_stopped_even_if_provider_stop_has_partial_failure() -> None:
    class _ErrorStopProvider(_ProviderStub):
        def stop(self, session: TunnelSession) -> None:
            self.stop_calls += 1
            raise RuntimeError("stop failed")

    session = _build_session()
    provider = _ErrorStopProvider(session)
    manager = TunnelManager(provider=provider, provider_name="cloudflare", default_local_url="http://localhost:8501")
    manager.session = session

    manager.stop()

    assert manager.session is not None
    assert manager.session.status == TunnelStatus.STOPPED
    assert manager.session.pid is None


def test_duplicate_start_is_prevented_for_running_and_warning() -> None:
    session = _build_session(status=TunnelStatus.WARNING)
    provider = _ProviderStub(session)
    manager = TunnelManager(provider=provider, provider_name="cloudflare", default_local_url="http://localhost:8501")
    manager.session = session

    returned = manager.start()

    assert returned is session
    assert provider.start_calls == 0


def test_start_rotates_stale_session_with_dead_public_url() -> None:
    existing = _build_session(status=TunnelStatus.RUNNING)
    replacement = _build_session(status=TunnelStatus.RUNNING)
    replacement.public_url = "https://fresh.trycloudflare.com"

    provider = _ProviderStub(replacement)
    manager = TunnelManager(provider=provider, provider_name="cloudflare", default_local_url="http://localhost:8501")
    manager.session = existing

    def _stale_status(_session: TunnelSession) -> TunnelStatus:
        return TunnelStatus.STALE

    provider.get_status = _stale_status  # type: ignore[method-assign]

    started = manager.start()

    assert started is replacement
    assert provider.start_calls == 1
    assert manager.session is replacement


def test_sync_public_share_sidebar_state_for_running_session(monkeypatch) -> None:
    fake_state: dict[str, object] = {}

    class _FakeStreamlit:
        session_state = fake_state

    session = _build_session(status=TunnelStatus.RUNNING)

    class _AliveProcess:
        def poll(self):
            return None

    session.process = _AliveProcess()  # type: ignore[assignment]
    session.pid = None
    provider = _ProviderStub(session)
    manager = TunnelManager(provider=provider, provider_name="cloudflare", default_local_url="http://localhost:8501")
    manager.session = session

    import sys

    monkeypatch.setitem(sys.modules, "streamlit", _FakeStreamlit())

    sync_public_share_sidebar_state(manager)

    assert fake_state["public_share_url"] == "https://demo.trycloudflare.com"
    assert fake_state["public_share_status"] == TunnelStatus.RUNNING.value
    assert fake_state["public_share_active"] is True


def test_sync_public_share_sidebar_state_for_stale_session(monkeypatch) -> None:
    fake_state: dict[str, object] = {}

    class _FakeStreamlit:
        session_state = fake_state

    session = _build_session(status=TunnelStatus.STALE)
    session.public_url = None
    provider = _ProviderStub(session)
    manager = TunnelManager(provider=provider, provider_name="cloudflare", default_local_url="http://localhost:8501")
    manager.session = session

    import sys

    monkeypatch.setitem(sys.modules, "streamlit", _FakeStreamlit())

    sync_public_share_sidebar_state(manager)

    assert fake_state["public_share_url"] is None
    assert fake_state["public_share_status"] == TunnelStatus.STALE.value
    assert fake_state["public_share_active"] is False
