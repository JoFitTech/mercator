"""Tests für die getrennte Datenbankstatus-Prüfung."""

from __future__ import annotations

from src.config.settings import MySqlTargetSettings, Settings
from src.services.database_status_service import DatabaseStatusService


class _MongoDbStub:
    """Stellt ein minimales MongoDB-Testdouble bereit."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def command(self, _cmd: str) -> dict[str, int]:
        if self.should_fail:
            raise RuntimeError("mongo down")
        return {"ok": 1}


class _MongoClientStub:
    """Gibt eine steuerbare MongoDB-Instanz zurück."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def get_database(self) -> _MongoDbStub:
        return _MongoDbStub(should_fail=self.should_fail)


def _build_settings(active_target: str = "local", fallback: bool = True) -> Settings:
    """Erzeugt reproduzierbare MySQL-Testsettings."""

    return Settings(
        mysql_active_target=active_target,
        mysql_auto_fallback_to_local=fallback,
        mysql_sync_enabled=True,
        local_mysql=MySqlTargetSettings(
            name="local",
            host="localhost",
            port=3306,
            database="mercator_local",
            user="root",
            password="secret",
            connect_timeout=10,
            create_database=False,
            ssl_disabled=True,
            ssl_ca=None,
            ssl_cert=None,
            ssl_key=None,
        ),
        uni_mysql=MySqlTargetSettings(
            name="uni",
            host="uni-host",
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


def test_database_status_service_reports_split_status(monkeypatch) -> None:
    """Prüft, dass MySQL und MongoDB getrennt als verbunden gemeldet werden."""

    monkeypatch.setattr(
        "src.services.database_status_service.resolve_active_mysql_target",
        lambda settings, requested_target: type(
            "Resolution",
            (),
            {
                "requested_target": requested_target,
                "active_target": "local",
                "client": object(),
                "used_fallback": False,
                "messages": ["local ok"],
            },
        )(),
    )

    service = DatabaseStatusService()
    status, resolution = service.evaluate(
        mysql_settings=_build_settings(active_target="local"),
        mongo_client=_MongoClientStub(should_fail=False),
        requested_target="local",
    )

    assert status.mysql.is_connected is True
    assert status.mysql.active_target == "local"
    assert status.mongo.is_connected is True
    assert resolution is not None


def test_database_status_service_flags_mongo_as_warning(monkeypatch) -> None:
    """Prüft, dass ein Mongo-Ausfall getrennt vom MySQL-Status behandelt wird."""

    monkeypatch.setattr(
        "src.services.database_status_service.resolve_active_mysql_target",
        lambda settings, requested_target: type(
            "Resolution",
            (),
            {
                "requested_target": requested_target,
                "active_target": "local",
                "client": object(),
                "used_fallback": False,
                "messages": ["local ok"],
            },
        )(),
    )

    service = DatabaseStatusService()
    status, _resolution = service.evaluate(
        mysql_settings=_build_settings(active_target="local"),
        mongo_client=_MongoClientStub(should_fail=True),
        requested_target="local",
    )

    assert status.mysql.is_connected is True
    assert status.mongo.is_connected is False
    assert "nicht erreichbar" in status.mongo.message
