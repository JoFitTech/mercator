from __future__ import annotations

from datetime import datetime, timezone

from src.services.public_share_service import (
    CloudflareQuickTunnelProvider,
    TunnelManager,
    TunnelSession,
    TunnelStatus,
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


def test_get_status_transitions_to_stale_when_process_died() -> None:
    class _DeadProcess:
        def poll(self):
            return 1

    provider = CloudflareQuickTunnelProvider()
    session = TunnelSession(
        provider="cloudflare",
        local_url="http://localhost:8501",
        public_url="https://demo.trycloudflare.com",
        pid=123,
        started_at=datetime.now(timezone.utc),
        status=TunnelStatus.RUNNING,
        raw_log_tail=[],
        process=_DeadProcess(),  # type: ignore[arg-type]
    )

    status = provider.get_status(session)

    assert status == TunnelStatus.STALE


def test_stop_logic_sets_stopped_even_if_provider_stop_has_partial_failure() -> None:
    class _ErrorStopProvider(_ProviderStub):
        def stop(self, session: TunnelSession) -> None:
            self.stop_calls += 1
            raise RuntimeError("stop failed")

    session = TunnelSession(
        provider="cloudflare",
        local_url="http://localhost:8501",
        public_url="https://demo.trycloudflare.com",
        pid=11,
        started_at=datetime.now(timezone.utc),
        status=TunnelStatus.RUNNING,
        raw_log_tail=[],
    )
    provider = _ErrorStopProvider(session)
    manager = TunnelManager(provider=provider, provider_name="cloudflare", default_local_url="http://localhost:8501")
    manager.session = session

    manager.stop()

    assert manager.session is not None
    assert manager.session.status == TunnelStatus.STOPPED


def test_duplicate_start_is_prevented() -> None:
    session = TunnelSession(
        provider="cloudflare",
        local_url="http://localhost:8501",
        public_url="https://demo.trycloudflare.com",
        pid=22,
        started_at=datetime.now(timezone.utc),
        status=TunnelStatus.RUNNING,
        raw_log_tail=[],
    )
    provider = _ProviderStub(session)
    manager = TunnelManager(provider=provider, provider_name="cloudflare", default_local_url="http://localhost:8501")
    manager.session = session

    returned = manager.start()

    assert returned is session
    assert provider.start_calls == 0
