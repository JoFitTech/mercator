"""Tests fuer Admin-Loeschlogik (FK-Schutz und Review-Mode-Blockade)."""

from __future__ import annotations

from contextlib import contextmanager

from src.config.settings import AppSettings, EnrichmentConfig, FmpConfig, GateConfig, MongoConfig, MySqlTargetSettings, Settings
from src.services.public_share_service import TunnelSession, TunnelStatus
from src.ui.pages.admin_page import (
    AdminDashboardService,
    _public_share_error_feedback,
    _public_share_status_message,
    _resolve_share_file_path,
)


class _CursorStub:
    def __init__(self, ref_count: int) -> None:
        self.ref_count = ref_count
        self.executed_sql: list[str] = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql: str) -> None:
        normalized = " ".join(sql.split())
        self.executed_sql.append(normalized)
        if normalized.upper().startswith("DELETE FROM COMPANIES"):
            self.rowcount = 5

    def fetchone(self):
        return {"ref_count": self.ref_count}


class _ConnectionStub:
    def __init__(self, ref_count: int) -> None:
        self.cursor_instance = _CursorStub(ref_count=ref_count)
        self.committed = False

    def cursor(self, dictionary: bool = False):
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True


class _MySqlClientStub:
    def __init__(self, ref_count: int) -> None:
        self.conn = _ConnectionStub(ref_count=ref_count)

    @contextmanager
    def connection(self, include_database: bool = True):
        yield self.conn


def _build_settings(review_mode: bool = False, disable_admin_delete: bool = False) -> AppSettings:
    mysql_settings = Settings(
        mysql_active_target="local",
        mysql_auto_fallback_to_local=True,
        mysql_sync_enabled=True,
        local_mysql=MySqlTargetSettings(
            name="local",
            host="localhost",
            port=3306,
            database="mercator_local",
            user="root",
            password="secret",
            connect_timeout=5,
            create_database=False,
            ssl_disabled=True,
            ssl_ca=None,
            ssl_cert=None,
            ssl_key=None,
        ),
        uni_mysql=MySqlTargetSettings(
            name="uni",
            host="uni",
            port=3306,
            database="mercator_uni",
            user="root",
            password="secret",
            connect_timeout=5,
            create_database=False,
            ssl_disabled=True,
            ssl_ca=None,
            ssl_cert=None,
            ssl_key=None,
        ),
    )
    return AppSettings(
        app_env="test",
        app_title="Mercator",
        dataset_path="data/raw",
        project_root=__import__("pathlib").Path("."),
        mysql=mysql_settings,
        mongo=MongoConfig(active_target="local", uri="mongodb://localhost:27017/", database="mercator"),
        fmp=FmpConfig(base_url="https://example.test", api_key="abc", api_key_source="env"),
        enrichment=EnrichmentConfig(),
        gate=GateConfig(),
        review_mode=review_mode,
        disable_import=False,
        disable_admin_delete=disable_admin_delete,
        ui_test_mode=False,
        trade_republic_universe_url="https://assets.traderepublic.com/assets/files/DE/Instrument_Universe_DE_en.csv",
        trade_republic_refresh_ttl_hours=24,
    )


def test_clear_mysql_companies_blocks_when_fk_references_exist() -> None:
    service = AdminDashboardService(
        settings=_build_settings(),
        mysql_client=_MySqlClientStub(ref_count=3),
        mongo_available=False,
    )

    success, message = service.clear_mysql_companies()

    assert success is False
    assert "3 insider_trades" in message
    assert all("DELETE FROM companies" not in sql for sql in service.mysql_client.conn.cursor_instance.executed_sql)


def test_clear_mysql_companies_blocked_in_review_mode() -> None:
    service = AdminDashboardService(
        settings=_build_settings(review_mode=True, disable_admin_delete=True),
        mysql_client=_MySqlClientStub(ref_count=0),
        mongo_available=False,
    )

    success, message = service.clear_mysql_companies()

    assert success is False
    assert "deaktiviert" in message.lower()


def test_clear_mysql_companies_blocked_when_pending_startup_sync(monkeypatch) -> None:
    service = AdminDashboardService(
        settings=_build_settings(),
        mysql_client=_MySqlClientStub(ref_count=0),
        mongo_available=False,
    )
    monkeypatch.setattr(service, "_pending_sync_blocks_deletes", lambda: True)

    success, message = service.clear_mysql_companies()

    assert success is False
    assert "pending" in message.lower()


def _build_tunnel_session() -> TunnelSession:
    from datetime import datetime, timezone

    return TunnelSession(
        provider="cloudflare",
        local_url="http://localhost:8501",
        public_url="https://demo.trycloudflare.com",
        pid=123,
        started_at=datetime.now(timezone.utc),
        status=TunnelStatus.WARNING,
        raw_log_tail=[],
        error_message="diagnostic",
    )


def test_public_share_error_feedback_uses_warning_for_container_public_check_failures() -> None:
    session = _build_tunnel_session()
    session.last_process_alive = True
    session.last_local_healthcheck_ok = True
    session.last_public_healthcheck_ok = False
    session.last_public_check_type = "dns_temporary"

    level, message = _public_share_error_feedback(session)

    assert level == "warning"
    assert "Public-Health" in message


def test_public_share_error_feedback_prioritizes_cloudflare_1033() -> None:
    session = _build_tunnel_session()
    session.last_process_alive = True
    session.last_public_healthcheck_ok = False
    session.last_public_check_type = "cloudflare_1033"

    level, message = _public_share_error_feedback(session)

    assert level == "error"
    assert "1033" in message


def test_public_share_error_feedback_prioritizes_cloudflare_530_as_error() -> None:
    session = _build_tunnel_session()
    session.last_process_alive = True
    session.last_local_healthcheck_ok = True
    session.last_public_healthcheck_ok = False
    session.last_public_check_type = "cloudflare_530"

    level, message = _public_share_error_feedback(session)

    assert level == "error"
    assert "530" in message


def test_public_share_error_feedback_process_dead_is_error() -> None:
    session = _build_tunnel_session()
    session.last_process_alive = False
    session.last_public_healthcheck_ok = False

    level, message = _public_share_error_feedback(session)

    assert level == "error"
    assert "beendet" in message


def test_public_share_error_feedback_local_app_failure_is_error() -> None:
    session = _build_tunnel_session()
    session.last_process_alive = True
    session.last_local_healthcheck_ok = False
    session.last_public_healthcheck_ok = True

    level, message = _public_share_error_feedback(session)

    assert level == "error"
    assert "Lokale App" in message


def test_public_share_status_message_for_warning() -> None:
    level, message = _public_share_status_message(TunnelStatus.WARNING)
    assert level == "warning"
    assert "Warnungen" in message


def test_resolve_share_file_path_relative() -> None:
    base = __import__("pathlib").Path("/tmp/repo")
    resolved = _resolve_share_file_path(base, ".mercator/public-share/status.json")
    assert str(resolved).endswith(".mercator/public-share/status.json")
