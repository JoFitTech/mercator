"""Tests für die Resolver-Logik zur aktiven MySQL-Target-Auswahl."""

from __future__ import annotations

import pytest

from src.config.settings import MySqlTargetSettings, Settings, SettingsError
from src.db.mysql_target_resolver import resolve_active_target


class _ClientStub:
    """Einfaches Testdouble für MySQL-Clients im Resolver."""

    def __init__(self, target_name: str, status_by_target: dict[str, tuple[bool, str]]) -> None:
        self.target_name = target_name
        self._status_by_target = status_by_target

    def test_connection(self) -> tuple[bool, str]:
        return self._status_by_target[self.target_name]


def _build_settings(active_target: str = "local", fallback: bool = True) -> Settings:
    return Settings(
        mysql_active_target=active_target,
        mysql_auto_fallback_to_local=fallback,
        mysql_sync_enabled=False,
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


def test_resolver_returns_active_target_when_reachable(monkeypatch) -> None:
    """Prüft, dass ein erreichbares aktives Target direkt genutzt wird."""

    status = {
        "local": (True, "local ok"),
        "uni": (True, "uni ok"),
    }

    monkeypatch.setattr(
        "src.db.mysql_target_resolver.build_mysql_client_for_target",
        lambda settings, target_name: _ClientStub(target_name, status),
    )

    target_name, _client, messages = resolve_active_target(_build_settings(active_target="local"))

    assert target_name == "local"
    assert "local ok" in messages


def test_resolver_falls_back_to_local_when_uni_is_unreachable(monkeypatch) -> None:
    """Prüft das Fallback auf local, wenn uni ausfällt und Fallback aktiv ist."""

    status = {
        "local": (True, "local ok"),
        "uni": (False, "uni down"),
    }

    monkeypatch.setattr(
        "src.db.mysql_target_resolver.build_mysql_client_for_target",
        lambda settings, target_name: _ClientStub(target_name, status),
    )

    target_name, _client, messages = resolve_active_target(_build_settings(active_target="uni", fallback=True))

    assert target_name == "local"
    assert any("Falling back" in message for message in messages)


def test_resolver_raises_without_fallback(monkeypatch) -> None:
    """Prüft den Fehlerpfad, wenn das aktive Ziel ausfällt und kein Fallback erlaubt ist."""

    status = {
        "local": (True, "local ok"),
        "uni": (False, "uni down"),
    }

    monkeypatch.setattr(
        "src.db.mysql_target_resolver.build_mysql_client_for_target",
        lambda settings, target_name: _ClientStub(target_name, status),
    )

    with pytest.raises(SettingsError):
        resolve_active_target(_build_settings(active_target="uni", fallback=False))
