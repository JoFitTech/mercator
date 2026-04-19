from __future__ import annotations

from src.app.infrastructure_mode import build_infrastructure_mode
from src.config.settings import AppSettings, EnrichmentConfig, FmpConfig, GateConfig, MongoConfig, MySqlTargetSettings, Settings
from src.services.app_settings_service import AppSettingsService
from src.services.database_status_service import DatabaseStatus, MongoStatus, MySqlStatus
from src.ui.pages.admin_page import compute_admin_capabilities


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


def test_infrastructure_mode_marks_offline_states() -> None:
    status = DatabaseStatus(
        mysql=MySqlStatus("local", None, False, False, ["offline"]),
        mongo=MongoStatus(is_connected=True, message="ok"),
    )
    mode = build_infrastructure_mode(status)
    assert mode.mysql_online is False
    assert mode.mongo_online is True
    assert mode.analysis_available is False
    assert mode.import_available is False
    assert mode.settings_persistence_available is False
    assert mode.write_available is False


def test_session_only_settings_persist_within_session(monkeypatch) -> None:
    session: dict = {}
    monkeypatch.setattr(AppSettingsService, "_session_state", staticmethod(lambda: session))
    service = AppSettingsService(runtime_repo=None, filter_repo=None, defaults=_build_settings())

    runtime = service.defaults_runtime()
    runtime.min_trade_value = 222000
    service.save(runtime)

    loaded = service.load()
    assert loaded.min_trade_value == 222000
    assert service.is_persistence_available() is False


def test_admin_capabilities_disable_write_when_one_db_offline() -> None:
    status = DatabaseStatus(
        mysql=MySqlStatus("local", "local", True, False, []),
        mongo=MongoStatus(is_connected=False, message="offline"),
    )

    class _SettingsServiceStub:
        @staticmethod
        def is_persistence_available() -> bool:
            return True

    caps = compute_admin_capabilities(
        db_status=status,
        mysql_client=object(),  # wird bei db_status ignoriert
        mongo_available=False,
        settings_service=_SettingsServiceStub(),
    )

    assert caps["mysql_online"] is True
    assert caps["mongo_online"] is False
    assert caps["write_available"] is False
    assert caps["persistence_available"] is True
