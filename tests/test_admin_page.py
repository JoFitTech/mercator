"""Tests fuer Admin-Loeschlogik (FK-Schutz und Review-Mode-Blockade)."""

from __future__ import annotations

from contextlib import contextmanager

from src.config.settings import AppSettings, FmpConfig, GateConfig, MongoConfig, MySqlTargetSettings, Settings
from src.ui.pages.admin_page import AdminDashboardService


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
