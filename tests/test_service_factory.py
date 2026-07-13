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


class _MySqlClientSchemaSpy:
    def __init__(self) -> None:
        self.initialize_calls = 0

    def initialize_schema(self) -> list[str]:
        self.initialize_calls += 1
        return []


class _MySqlClientSchemaFail:
    def initialize_schema(self) -> list[str]:
        raise RuntimeError("schema boom")


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
        trade_republic_refresh_ttl_hours=24,
        trade_republic_universe_local_csv="data/reference/trade_republic/trade_republic_stocks.csv",
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
                api2_firing_mode="ONLY PASS",
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

    monkeypatch.setattr(factory_module, "PreferenceScoreRepository", lambda _client: "preference-repo")

    def _dashboard_service_stub(raw_repo, company_mongo_repo, trade_repo, company_repo, **kwargs):
        captured["raw_repo"] = raw_repo
        captured["company_mongo_repo"] = company_mongo_repo
        captured["trade_repo"] = trade_repo
        captured["company_repo"] = company_repo
        captured["preference_score_repo"] = kwargs.get("preference_score_repo")
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
    assert captured["preference_score_repo"] == "preference-repo"


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


def test_import_service_runs_mysql_schema_migration_once_before_creation(monkeypatch) -> None:
    settings = _build_settings()
    mysql_spy = _MySqlClientSchemaSpy()

    monkeypatch.setattr(factory_module, "InsiderTradeMongoRepository", lambda _client: object())
    monkeypatch.setattr(factory_module, "CompanyMongoRepository", lambda _client: object())
    monkeypatch.setattr(factory_module, "InsiderTradeMySqlRepository", lambda _client: object())
    monkeypatch.setattr(factory_module, "CompanyMySqlRepository", lambda _client: object())
    monkeypatch.setattr(factory_module, "TradeRepublicUniverseIngestionService", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(factory_module, "TradeRepublicUniverseMatchingService", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(factory_module, "CompanyEnrichmentService", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(factory_module, "ImportService", lambda **_kwargs: object())

    class _RuntimeSettingsServiceStub:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def load(self):
            return SimpleNamespace(
                profile_ttl_days=7,
                lookup_mode="cik_primary_symbol_fallback",
                profile_gate_filter_statuses=("PASS",),
                api2_firing_mode="PASS + PENDING",
            )

        def load_score_gate_policy(self):
            return ScoreGatePolicy()

    monkeypatch.setattr(factory_module, "AppSettingsService", _RuntimeSettingsServiceStub)
    monkeypatch.setattr(factory_module, "FmpClient", lambda *_args, **_kwargs: object())

    service_factory = factory_module.ServiceFactory(
        settings=settings,
        mysql_client=mysql_spy,
        mongo_wrapper=object(),
    )

    first = service_factory.create_import_service()
    second = service_factory.create_import_service()

    assert first is not None
    assert second is not None
    assert mysql_spy.initialize_calls == 1


def test_import_service_is_disabled_when_mysql_schema_migration_fails() -> None:
    settings = _build_settings()

    service_factory = factory_module.ServiceFactory(
        settings=settings,
        mysql_client=_MySqlClientSchemaFail(),
        mongo_wrapper=object(),
    )

    import_service = service_factory.create_import_service()

    assert import_service is None
    assert factory_module.ServiceFactory.last_import_issue is not None
    assert "MySQL-Schema-Migration fehlgeschlagen" in factory_module.ServiceFactory.last_import_issue


def test_stock_import_service_is_created_with_clean_repositories(monkeypatch) -> None:
    settings = _build_settings()
    settings = __import__("dataclasses").replace(
        settings,
        fmp=FmpConfig(base_url="https://example.test", api_key="real-test-key", api_key_source="env"),
    )
    mysql_spy = _MySqlClientSchemaSpy()
    captured: dict[str, object] = {}

    monkeypatch.setattr(factory_module, "RawProviderResponseMongoRepository", lambda client: ("raw", client))
    monkeypatch.setattr(factory_module, "CompanyMySqlRepository", lambda client: ("company", client))
    monkeypatch.setattr(factory_module, "StockPriceRepository", lambda client: ("prices", client))
    monkeypatch.setattr(factory_module, "FundamentalMetricsRepository", lambda client: ("metrics", client))
    monkeypatch.setattr(factory_module, "ImportRunRepository", lambda client: ("runs", client))
    monkeypatch.setattr(factory_module, "DataQualityRepository", lambda client: ("quality", client))
    monkeypatch.setattr(factory_module, "FmpClient", lambda *_args, **_kwargs: "fmp")

    def _stock_import_service_stub(**kwargs):
        captured.update(kwargs)
        return "stock-import-service"

    monkeypatch.setattr(factory_module, "StockImportService", _stock_import_service_stub)

    service_factory = factory_module.ServiceFactory(settings=settings, mysql_client=mysql_spy, mongo_wrapper=object())

    service = service_factory.create_stock_import_service()

    assert service == "stock-import-service"
    assert captured["fmp_client"] == "fmp"
    assert captured["raw_repository"][0] == "raw"
    assert captured["company_repository"][0] == "company"
    assert captured["price_repository"][0] == "prices"
    assert captured["metrics_repository"][0] == "metrics"
    assert mysql_spy.initialize_calls == 1


def test_stock_import_service_disabled_with_clear_reason_when_mongo_missing() -> None:
    settings = _build_settings()

    service_factory = factory_module.ServiceFactory(settings=settings, mysql_client=_MySqlClientStub(), mongo_wrapper=None)

    service = service_factory.create_stock_import_service()

    assert service is None
    assert factory_module.ServiceFactory.last_import_issue == (
        "StockImportService deaktiviert: Mongo-Client fehlt (raw provider responses nicht verfuegbar)."
    )


def test_prediction_and_backtest_services_are_created_with_clean_repositories(monkeypatch) -> None:
    settings = _build_settings()
    mysql_client = _MySqlClientStub()
    captured_prediction: dict[str, object] = {}
    captured_backtest: dict[str, object] = {}
    captured_preference: dict[str, object] = {}

    monkeypatch.setattr(factory_module, "PredictionRepository", lambda client: ("predictions", client))
    monkeypatch.setattr(factory_module, "PreferenceScoreRepository", lambda client: ("preferences", client))
    monkeypatch.setattr(factory_module, "TechnicalFeatureRepository", lambda client: ("technical", client))
    monkeypatch.setattr(factory_module, "FundamentalFeatureRepository", lambda client: ("fundamental", client))
    monkeypatch.setattr(factory_module, "WatchlistRepository", lambda client: ("watchlist", client))
    monkeypatch.setattr(factory_module, "DataQualityRepository", lambda client: ("quality", client))
    monkeypatch.setattr(factory_module, "StockPriceRepository", lambda client: ("prices", client))
    monkeypatch.setattr(factory_module, "BacktestRepository", lambda client: ("backtests", client))

    def _prediction_service_stub(**kwargs):
        captured_prediction.update(kwargs)
        return "prediction-service"

    def _backtest_service_stub(**kwargs):
        captured_backtest.update(kwargs)
        return "backtest-service"

    def _preference_service_stub(**kwargs):
        captured_preference.update(kwargs)
        return "preference-service"

    monkeypatch.setattr(factory_module, "PredictionModelService", _prediction_service_stub)
    monkeypatch.setattr(factory_module, "BacktestService", _backtest_service_stub)
    monkeypatch.setattr(factory_module, "PreferenceScoringService", _preference_service_stub)

    service_factory = factory_module.ServiceFactory(settings=settings, mysql_client=mysql_client, mongo_wrapper=None)

    assert service_factory.create_prediction_model_service() == "prediction-service"
    assert service_factory.create_backtest_service() == "backtest-service"
    assert service_factory.create_preference_scoring_service() == "preference-service"
    assert captured_prediction["prediction_repository"] == ("predictions", mysql_client)
    assert captured_prediction["technical_feature_repository"] == ("technical", mysql_client)
    assert captured_prediction["fundamental_feature_repository"] == ("fundamental", mysql_client)
    assert captured_prediction["watchlist_repository"] == ("watchlist", mysql_client)
    assert captured_backtest["prediction_repository"] == ("predictions", mysql_client)
    assert captured_backtest["price_repository"] == ("prices", mysql_client)
    assert captured_backtest["backtest_repository"] == ("backtests", mysql_client)
    assert captured_preference["preference_repository"] == ("preferences", mysql_client)
    assert captured_preference["prediction_repository"] == ("predictions", mysql_client)
    assert captured_preference["watchlist_repository"] == ("watchlist", mysql_client)


def test_stock_analysis_detail_and_model_evaluation_repositories_are_wired(monkeypatch) -> None:
    settings = _build_settings()
    mysql_client = _MySqlClientStub()
    captured: dict[str, object] = {}

    monkeypatch.setattr(factory_module, "WatchlistRepository", lambda client: ("watchlist", client))
    monkeypatch.setattr(factory_module, "DataQualityRepository", lambda client: ("quality", client))
    monkeypatch.setattr(factory_module, "CompanyMySqlRepository", lambda client: ("company", client))
    monkeypatch.setattr(factory_module, "StockPriceRepository", lambda client: ("prices", client))
    monkeypatch.setattr(factory_module, "TechnicalFeatureRepository", lambda client: ("technical", client))
    monkeypatch.setattr(factory_module, "FundamentalFeatureRepository", lambda client: ("fundamental", client))
    monkeypatch.setattr(factory_module, "PredictionRepository", lambda client: ("predictions", client))
    monkeypatch.setattr(factory_module, "PreferenceScoreRepository", lambda client: ("preferences", client))
    monkeypatch.setattr(factory_module, "BacktestRepository", lambda client: ("backtests", client))

    def _stock_analysis_stub(watchlist_repository, data_quality_repository, **kwargs):
        captured["watchlist_repository"] = watchlist_repository
        captured["data_quality_repository"] = data_quality_repository
        captured.update(kwargs)
        return "stock-analysis-service"

    monkeypatch.setattr(factory_module, "StockAnalysisService", _stock_analysis_stub)
    service_factory = factory_module.ServiceFactory(settings=settings, mysql_client=mysql_client, mongo_wrapper=None)

    assert service_factory.create_stock_analysis_service() == "stock-analysis-service"
    assert captured["company_repository"] == ("company", mysql_client)
    assert captured["price_repository"] == ("prices", mysql_client)
    assert captured["technical_feature_repository"] == ("technical", mysql_client)
    assert captured["fundamental_feature_repository"] == ("fundamental", mysql_client)
    assert captured["prediction_repository"] == ("predictions", mysql_client)
    assert captured["preference_repository"] == ("preferences", mysql_client)
    assert service_factory.create_prediction_repository() == ("predictions", mysql_client)
    assert service_factory.create_backtest_repository() == ("backtests", mysql_client)
