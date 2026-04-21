"""Tests für die Resolver-Logik zur aktiven Mongo-Target-Auswahl."""

from __future__ import annotations

import pytest

from src.config.settings import MongoSettings, MongoTargetSettings, SettingsError
from src.db.mongo_target_resolver import resolve_active_mongo_target


class _MongoDbStub:
    def __init__(self, should_fail: bool = False, error: Exception | None = None) -> None:
        self.should_fail = should_fail
        self.error = error

    def command(self, _cmd: str) -> dict[str, int]:
        if self.error is not None:
            raise self.error
        if self.should_fail:
            raise RuntimeError("mongo down")
        return {"ok": 1}


class _WrapperStub:
    def __init__(self, target_name: str, status_by_target: dict[str, tuple[bool, Exception | None]]) -> None:
        self.config = type("Config", (), {"active_target": target_name})()
        should_fail, error = status_by_target[target_name]
        self._db = _MongoDbStub(should_fail=should_fail, error=error)

    def get_database(self) -> _MongoDbStub:
        return self._db


def _build_settings(active_target: str = "uni", fallback: bool = True) -> MongoSettings:
    return MongoSettings(
        mongo_active_target=active_target,
        mongo_auto_fallback_to_local=fallback,
        local_mongo=MongoTargetSettings(name="local", uri="mongodb://localhost:27017/", database="mercator"),
        uni_mongo=MongoTargetSettings(
            name="uni",
            uri="mongodb://uni.example:27017/?authSource=admin",
            database="uni_db",
        ),
    )


def test_resolver_returns_active_target_when_reachable(monkeypatch) -> None:
    status = {"uni": (False, None), "local": (False, None)}
    monkeypatch.setattr(
        "src.db.mongo_target_resolver.build_mongo_client_for_target",
        lambda settings, target_name: _WrapperStub(target_name, status),
    )

    resolved = resolve_active_mongo_target(_build_settings(active_target="uni"))

    assert resolved.requested_target == "uni"
    assert resolved.active_target == "uni"
    assert resolved.used_fallback is False


def test_resolver_falls_back_to_local_when_uni_is_unreachable(monkeypatch) -> None:
    status = {"uni": (True, None), "local": (False, None)}
    monkeypatch.setattr(
        "src.db.mongo_target_resolver.build_mongo_client_for_target",
        lambda settings, target_name: _WrapperStub(target_name, status),
    )

    resolved = resolve_active_mongo_target(_build_settings(active_target="uni", fallback=True))

    assert resolved.requested_target == "uni"
    assert resolved.active_target == "local"
    assert resolved.used_fallback is True


def test_resolver_raises_without_fallback(monkeypatch) -> None:
    status = {"uni": (True, None), "local": (False, None)}
    monkeypatch.setattr(
        "src.db.mongo_target_resolver.build_mongo_client_for_target",
        lambda settings, target_name: _WrapperStub(target_name, status),
    )

    with pytest.raises(SettingsError):
        resolve_active_mongo_target(_build_settings(active_target="uni", fallback=False))


def test_resolver_raises_when_active_and_fallback_unreachable(monkeypatch) -> None:
    status = {"uni": (True, None), "local": (True, None)}
    monkeypatch.setattr(
        "src.db.mongo_target_resolver.build_mongo_client_for_target",
        lambda settings, target_name: _WrapperStub(target_name, status),
    )

    with pytest.raises(SettingsError):
        resolve_active_mongo_target(_build_settings(active_target="uni", fallback=True))
