from __future__ import annotations

import re

import pytest

from src.config.settings import AppSettings, EnrichmentConfig, FmpConfig, GateConfig, MongoConfig, MySqlTargetSettings, Settings
from src.db.repositories.settings_repository import AppRuntimePreferencesRepository
from src.services.app_settings_service import AppSettingsService


class _RuntimeRepoOk:
    def load(self, key: str):
        if key == "runtime_settings":
            return {"min_trade_value": 777000, "lookup_mode": "symbol_only"}
        return None


class _RuntimeRepoError:
    def load(self, _key: str):
        raise RuntimeError("db unavailable")


class _FilterRepoError:
    def load(self, _scope: str, _key: str):
        raise RuntimeError("filter repo unavailable")


def _build_settings() -> AppSettings:
    mysql_settings = Settings(
        mysql_active_target="local",
        mysql_auto_fallback_to_local=True,
        mysql_sync_enabled=True,
        local_mysql=MySqlTargetSettings("local", "localhost", 3306, "mercator", "root", "secret", 5, False, True, None, None, None),
        uni_mysql=MySqlTargetSettings("uni", "localhost", 3306, "mercator", "root", "secret", 5, False, True, None, None, None),
    )
    return AppSettings(
        app_env="test",
        app_title="Mercator",
        dataset_path=".",
        project_root=__import__("pathlib").Path("."),
        mysql=mysql_settings,
        mongo=MongoConfig(active_target="local", uri="mongodb://localhost:27017", database="mercator"),
        fmp=FmpConfig(base_url="https://example", api_key="abc", api_key_source="env"),
        enrichment=EnrichmentConfig(),
        gate=GateConfig(),
        review_mode=False,
        disable_import=False,
        disable_admin_delete=False,
        ui_test_mode=False,
        trade_republic_universe_url="https://assets.traderepublic.com/assets/files/DE/Instrument_Universe_DE_en.csv",
        trade_republic_refresh_ttl_hours=24,
    )


def test_load_uses_repository_payload_when_available() -> None:
    service = AppSettingsService(runtime_repo=_RuntimeRepoOk(), filter_repo=None, defaults=_build_settings())
    runtime = service.load()
    assert runtime.min_trade_value == 777000
    assert runtime.lookup_mode == "symbol_only"


def test_load_falls_back_to_defaults_on_repository_error() -> None:
    service = AppSettingsService(runtime_repo=_RuntimeRepoError(), filter_repo=None, defaults=_build_settings())
    runtime = service.load()
    assert runtime == service.defaults_runtime()


def test_load_score_gate_policy_falls_back_to_defaults_on_repository_error() -> None:
    service = AppSettingsService(runtime_repo=_RuntimeRepoError(), filter_repo=None, defaults=_build_settings())
    policy = service.load_score_gate_policy()
    assert policy == service.defaults_score_gate_policy()


def test_load_filter_falls_back_to_default_on_repository_error() -> None:
    service = AppSettingsService(runtime_repo=None, filter_repo=_FilterRepoError(), defaults=_build_settings())
    assert service.load_filter("trades", "symbol", "AAPL") == "AAPL"


def test_settings_repository_raises_clear_error_for_invalid_client() -> None:
    repo = AppRuntimePreferencesRepository(client=object())
    with pytest.raises(RuntimeError, match="keine MySQL-Verbindung"):
        repo.load("runtime_settings")


def test_settings_repository_raises_clear_error_when_client_missing() -> None:
    repo = AppRuntimePreferencesRepository(client=None)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="MySQL-Client fehlt"):
        repo.load("runtime_settings")


def test_navigation_labels_do_not_contain_emojis() -> None:
    content = __import__("pathlib").Path("src/app/navigation.py").read_text(encoding="utf-8")
    emoji_pattern = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
    assert emoji_pattern.search(content) is None
