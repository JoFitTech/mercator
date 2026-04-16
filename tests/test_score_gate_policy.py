from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import AppSettings, FmpConfig, GateConfig, MongoConfig, MySqlTargetSettings, Settings
from src.domain_rules import ScoreGatePolicy, classify_score
from src.services.app_settings_service import AppSettingsService


@dataclass
class _RuntimeRepoStub:
    storage: dict

    def load(self, key: str):
        return self.storage.get(key)

    def upsert(self, payload: dict):
        self.storage[payload["preference_key"]] = payload["preference_value_json"]


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
        gate=GateConfig(),
        review_mode=False,
        disable_import=False,
        disable_admin_delete=False,
        ui_test_mode=False,
        trade_republic_universe_url="https://assets.traderepublic.com/assets/files/DE/Instrument_Universe_DE_en.csv",
        trade_republic_refresh_ttl_hours=24,
    )


def test_score_gate_policy_persistence_roundtrip() -> None:
    runtime_repo = _RuntimeRepoStub(storage={})
    service = AppSettingsService(runtime_repo=runtime_repo, filter_repo=None, defaults=_build_settings())

    policy = ScoreGatePolicy(score_threshold_hold_min=75, score_threshold_pass_min=92, gate_min_trade_value=250000)
    service.save_score_gate_policy(policy)
    loaded = service.load_score_gate_policy()

    assert loaded.score_threshold_hold_min == 75
    assert loaded.score_threshold_pass_min == 92
    assert loaded.gate_min_trade_value == 250000


def test_score_classification_thresholds() -> None:
    policy = ScoreGatePolicy(score_threshold_hold_min=70, score_threshold_pass_min=90)

    assert classify_score(69.9, policy)[0] == "FAIL"
    assert classify_score(70.0, policy)[0] == "HOLD"
    assert classify_score(90.0, policy)[0] == "PASS"
