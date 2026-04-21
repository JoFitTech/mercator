"""Tests für die getrennte Datenbankstatus-Prüfung."""

from __future__ import annotations

from pymongo.errors import InvalidURI, OperationFailure, ServerSelectionTimeoutError

from src.config.settings import MongoSettings, MongoTargetSettings, MySqlTargetSettings, Settings
from src.services.database_status_service import DatabaseStatusService


def _build_mongo_settings(active_target: str = "uni", fallback: bool = True) -> MongoSettings:
    return MongoSettings(
        mongo_active_target=active_target,
        mongo_auto_fallback_to_local=fallback,
        local_mongo=MongoTargetSettings(
            name="local",
            uri="mongodb://localhost:27017/",
            database="mercator",
        ),
        uni_mongo=MongoTargetSettings(
            name="uni",
            uri="mongodb://uni.example:27017/?authSource=admin",
            database="uni_db",
        ),
    )


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
    monkeypatch.setattr(
        "src.services.database_status_service.resolve_active_mongo_target",
        lambda settings, requested_target: type(
            "MongoResolution",
            (),
            {
                "requested_target": requested_target,
                "active_target": "uni",
                "client": object(),
                "used_fallback": False,
                "messages": ["uni ok"],
            },
        )(),
    )

    service = DatabaseStatusService()
    status, resolution, _mongo_resolution = service.evaluate(
        mysql_settings=_build_settings(active_target="local"),
        mongo_settings=_build_mongo_settings(),
        requested_target="local",
    )

    assert status.mysql.is_connected is True
    assert status.mysql.active_target == "local"
    assert status.mongo.is_connected is True
    assert status.mongo.requested_target == "uni"
    assert status.mongo.active_target == "uni"
    assert status.mongo.used_fallback is False
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
    monkeypatch.setattr(
        "src.services.database_status_service.resolve_active_mongo_target",
        lambda settings, requested_target: (_ for _ in ()).throw(RuntimeError("mongo down")),
    )

    status, _resolution, _mongo_resolution = service.evaluate(
        mysql_settings=_build_settings(active_target="local"),
        mongo_settings=_build_mongo_settings(),
        requested_target="local",
    )

    assert status.mysql.is_connected is True
    assert status.mongo.is_connected is False
    assert status.mongo.messages == ["Mongo Unbekannter Fehler"]


def test_database_status_service_classifies_invalid_mongo_uri(monkeypatch) -> None:
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
    monkeypatch.setattr(
        "src.services.database_status_service.resolve_active_mongo_target",
        lambda settings, requested_target: (_ for _ in ()).throw(InvalidURI("bad uri")),
    )
    status, _, _ = service.evaluate(
        mysql_settings=_build_settings(),
        mongo_settings=_build_mongo_settings(),
        requested_target="local",
    )
    assert status.mongo.messages == ["Mongo URI ungültig"]


def test_database_status_service_classifies_mongo_auth_error(monkeypatch) -> None:
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
    monkeypatch.setattr(
        "src.services.database_status_service.resolve_active_mongo_target",
        lambda settings, requested_target: (_ for _ in ()).throw(OperationFailure("Authentication failed.", code=18)),
    )
    status, _, _ = service.evaluate(
        mysql_settings=_build_settings(),
        mongo_settings=_build_mongo_settings(),
        requested_target="local",
    )
    assert status.mongo.messages == ["Mongo Authentifizierung fehlgeschlagen"]


def test_database_status_service_classifies_server_timeout(monkeypatch) -> None:
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
    monkeypatch.setattr(
        "src.services.database_status_service.resolve_active_mongo_target",
        lambda settings, requested_target: (_ for _ in ()).throw(ServerSelectionTimeoutError("timeout")),
    )
    status, _, _ = service.evaluate(
        mysql_settings=_build_settings(),
        mongo_settings=_build_mongo_settings(),
        requested_target="local",
    )
    assert status.mongo.messages == ["Mongo Host oder Port nicht erreichbar"]


def test_database_status_service_classifies_permission_error(monkeypatch) -> None:
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
    monkeypatch.setattr(
        "src.services.database_status_service.resolve_active_mongo_target",
        lambda settings, requested_target: (_ for _ in ()).throw(OperationFailure("not authorized", code=13)),
    )
    status, _, _ = service.evaluate(
        mysql_settings=_build_settings(),
        mongo_settings=_build_mongo_settings(),
        requested_target="local",
    )
    assert status.mongo.messages == ["Mongo verbunden, aber keine Berechtigung für Datenbank 'uni_db'"]
