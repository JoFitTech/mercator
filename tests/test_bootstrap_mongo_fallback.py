from __future__ import annotations

from pathlib import Path

from src.app import bootstrap as bootstrap_module
from src.config.settings import AppSettings, EnrichmentConfig, FmpConfig, GateConfig, MongoConfig, MongoSettings, MongoTargetSettings, MySqlTargetSettings, Settings
from src.db.mongo_target_resolver import MongoResolutionResult
from src.services.database_status_service import DatabaseStatus, MongoStatus, MySqlStatus


class _FactoryProbe:
    mongo_wrapper = None

    def __init__(self, *, settings, mysql_client, mongo_wrapper):
        _FactoryProbe.mongo_wrapper = mongo_wrapper


def _build_app_settings() -> AppSettings:
    mysql = Settings(
        mysql_active_target="uni",
        mysql_auto_fallback_to_local=True,
        mysql_sync_enabled=True,
        local_mysql=MySqlTargetSettings("local", "localhost", 3306, "mercator", "root", "secret", 5, False, True, None, None, None),
        uni_mysql=MySqlTargetSettings("uni", "uni-host", 3306, "mercator", "root", "secret", 5, False, True, None, None, None),
    )
    mongo_targets = MongoSettings(
        mongo_active_target="uni",
        mongo_auto_fallback_to_local=True,
        local_mongo=MongoTargetSettings("local", "mongodb://localhost:27017/", "mercator"),
        uni_mongo=MongoTargetSettings("uni", "mongodb://uni:27017/?authSource=admin", "uni_db"),
    )
    return AppSettings(
        app_env="test",
        app_title="Mercator",
        dataset_path=".",
        project_root=Path("."),
        mysql=mysql,
        mongo=MongoConfig(active_target="uni", uri="mongodb://uni:27017/?authSource=admin", database="uni_db"),
        fmp=FmpConfig(base_url="https://example", api_key="abc", api_key_source="env"),
        enrichment=EnrichmentConfig(),
        gate=GateConfig(),
        review_mode=False,
        disable_import=False,
        disable_admin_delete=False,
        ui_test_mode=False,
        trade_republic_universe_url="https://assets.traderepublic.com/assets/files/DE/Instrument_Universe_DE_en.csv",
        trade_republic_refresh_ttl_hours=24,
        mongo_targets=mongo_targets,
    )


def test_init_core_services_uses_resolved_mongo_wrapper_on_fallback(monkeypatch) -> None:
    settings = _build_app_settings()
    fallback_wrapper = object()

    monkeypatch.setattr(bootstrap_module.st, "session_state", {})

    def _fake_evaluate(self, *, mysql_settings, mongo_settings, requested_target):
        status = DatabaseStatus(
            mysql=MySqlStatus("uni", "uni", True, False, []),
            mongo=MongoStatus("uni", "local", True, True, ["fallback"]),
        )
        mysql_resolution = type(
            "MySqlResolution",
            (),
            {"client": object(), "requested_target": "uni", "active_target": "uni", "used_fallback": False, "messages": []},
        )()
        mongo_resolution = MongoResolutionResult(
            requested_target="uni",
            active_target="local",
            client=fallback_wrapper,
            used_fallback=True,
            messages=["fallback"],
        )
        return status, mysql_resolution, mongo_resolution

    monkeypatch.setattr(bootstrap_module.DatabaseStatusService, "evaluate", _fake_evaluate)
    monkeypatch.setattr(bootstrap_module, "ServiceFactory", _FactoryProbe)

    db_status, _mysql_res, _factory = bootstrap_module._init_core_services(settings)

    assert db_status.mongo.active_target == "local"
    assert db_status.mongo.used_fallback is True
    assert _FactoryProbe.mongo_wrapper is fallback_wrapper
