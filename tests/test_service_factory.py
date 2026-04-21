"""Tests fuer den ServiceFactory-Degraded-Mode bei FMP-Konfigurationsfehlern."""

from __future__ import annotations

from types import SimpleNamespace

from src.config.settings import (
    AppSettings,
    EnrichmentConfig,
    FmpConfig,
    GateConfig,
    MongoConfig,
    MySqlTargetSettings,
    Settings,
)
from src.domain_rules import ScoreGatePolicy
from src.services import factory as factory_module


class _MySqlClientStub:
    def initialize_schema(self) -> None:
        return None


def _build_settings() -> AppSettings:
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

    return AppSettings(
        app_env="test",
        app_title="Mercator",
        dataset_path="data/raw",
        project_root=__import__("pathlib").Path("."),
        mysql=mysql_settings,
        mongo=MongoConfig(active_target="local", uri="mongodb://localhost:27017/", database="mercator"),
        fmp=FmpConfig(base_url="https://example.test", api_key="placeholder", api_key_source="env"),
        enrichment=EnrichmentConfig(),
        gate=GateConfig(),
        review_mode=False,
        disable_import=False,
        disable_admin_delete=False,
        ui_test_mode=False,
        trade_republic_universe_url="https://assets.traderepublic.com/assets/files/DE/Instrument_Universe_DE_en.csv",
        trade_republic_refresh_ttl_hours=24,
    )


def test_build_all_disables_import_service_when_fmp_key_invalid(monkeypatch) -> None:
    settings = _build_settings()

    monkeypatch.setattr(factory_module, "InsiderTradeMongoRepository", lambda _client: object())
    monkeypatch.setattr(factory_module, "CompanyMongoRepository", lambda _client: object())
    monkeypatch.setattr(factory_module, "InsiderTradeMySqlRepository", lambda _client: object())
    monkeypatch.setattr(factory_module, "CompanyMySqlRepository", lambda _client: object())
    monkeypatch.setattr(factory_module, "AppFilterSettingsRepository", lambda _client: object())
    monkeypatch.setattr(factory_module, "AppRuntimePreferencesRepository", lambda _client: object())
    monkeypatch.setattr(factory_module, "DashboardService", lambda *_args: object())
    monkeypatch.setattr(factory_module, "AnalysisService", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(factory_module, "FmpClient", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid key")))

    class _RuntimeSettingsServiceStub:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def load(self):
            return SimpleNamespace(
                profile_ttl_days=7,
                lookup_mode="cik_primary_symbol_fallback",
                profile_gate_filter_statuses=("PASS",),
            )

        def load_score_gate_policy(self):
            return ScoreGatePolicy()

    monkeypatch.setattr(factory_module, "AppSettingsService", _RuntimeSettingsServiceStub)

    service_factory = factory_module.ServiceFactory(
        settings=settings,
        mysql_client=_MySqlClientStub(),
        mongo_wrapper=object(),
    )
    import_service = service_factory.create_import_service()

    assert import_service is None
    assert factory_module.ServiceFactory.last_import_issue is not None
    assert "FMP-Konfiguration ungueltig" in factory_module.ServiceFactory.last_import_issue


def test_dashboard_service_falls_back_when_mongo_repo_init_fails(monkeypatch) -> None:
    settings = _build_settings()

    monkeypatch.setattr(
        factory_module,
        "InsiderTradeMongoRepository",
        lambda _client: (_ for _ in ()).throw(RuntimeError("mongo down")),
    )
    monkeypatch.setattr(factory_module, "InsiderTradeMySqlRepository", lambda _client: object())
    monkeypatch.setattr(factory_module, "CompanyMySqlRepository", lambda _client: object())

    captured: dict[str, object | None] = {}

    def _dashboard_service_stub(raw_repo, company_mongo_repo, trade_repo, company_repo):
        captured["raw_repo"] = raw_repo
        captured["company_mongo_repo"] = company_mongo_repo
        captured["trade_repo"] = trade_repo
        captured["company_repo"] = company_repo
        return object()

    monkeypatch.setattr(factory_module, "DashboardService", _dashboard_service_stub)

    service_factory = factory_module.ServiceFactory(
        settings=settings,
        mysql_client=_MySqlClientStub(),
        mongo_wrapper=object(),
    )

    service = service_factory.create_dashboard_service()

    assert service is not None
    assert captured["raw_repo"] is None
    assert captured["company_mongo_repo"] is None
    assert captured["trade_repo"] is not None
    assert captured["company_repo"] is not None


def test_import_service_disabled_when_mongo_repo_init_fails(monkeypatch) -> None:
    settings = _build_settings()

    monkeypatch.setattr(factory_module, "InsiderTradeMySqlRepository", lambda _client: object())
    monkeypatch.setattr(factory_module, "CompanyMySqlRepository", lambda _client: object())
    monkeypatch.setattr(
        factory_module,
        "InsiderTradeMongoRepository",
        lambda _client: (_ for _ in ()).throw(RuntimeError("mongo down")),
    )

    service_factory = factory_module.ServiceFactory(
        settings=settings,
        mysql_client=_MySqlClientStub(),
        mongo_wrapper=object(),
    )

    import_service = service_factory.create_import_service()

    assert import_service is None
    assert factory_module.ServiceFactory.last_import_issue is not None
    assert "Mongo nicht erreichbar" in factory_module.ServiceFactory.last_import_issue


def test_import_service_disabled_with_clear_reason_when_mongo_client_missing() -> None:
    settings = _build_settings()

    service_factory = factory_module.ServiceFactory(
        settings=settings,
        mysql_client=_MySqlClientStub(),
        mongo_wrapper=None,
    )

    import_service = service_factory.create_import_service()

    assert import_service is None
    assert factory_module.ServiceFactory.last_import_issue == (
        "ImportService deaktiviert: Mongo-Client fehlt (raw pipeline nicht verfuegbar)."
    )
