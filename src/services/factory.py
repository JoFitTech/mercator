from __future__ import annotations
from dataclasses import replace

from src.config.settings import AppSettings
from src.data_sources.fmp_client import FmpClient
from src.data_sources.alpha_vantage_client import AlphaVantageClient
from src.data_sources.polygon_client import PolygonClient
from src.services.company_enrichment_service import CompanyEnrichmentService
from src.db.mongo_client import MongoClientWrapper
from src.db.mongo_repository import (
    CompanyMongoRepository,
    InsiderTradeMongoRepository,
    RawProviderResponseMongoRepository,
)
from src.db.mysql_client import MySqlClient
from src.db.repositories.company_repository import CompanyMySqlRepository
from src.db.repositories.backtest_repository import BacktestRepository
from src.db.repositories.data_quality_repository import DataQualityRepository
from src.db.repositories.feature_repository import FundamentalFeatureRepository, TechnicalFeatureRepository
from src.db.repositories.fundamental_metrics_repository import FundamentalMetricsRepository
from src.db.repositories.import_run_repository import ImportRunRepository
from src.db.repositories.prediction_repository import PredictionRepository
from src.db.repositories.preference_score_repository import PreferenceScoreRepository
from src.db.repositories.stock_price_repository import StockPriceRepository
from src.db.repositories.watchlist_repository import WatchlistRepository
from src.db.repositories.trade_repository import InsiderTradeMySqlRepository
from src.db.repositories.settings_repository import (
    AppFilterSettingsRepository,
    AppRuntimePreferencesRepository,
)
from src.db.repositories.api_usage_repository import ApiUsageRepository
from src.preprocessing import GateEvaluator, GateRules
from src.services.app_settings_service import AppSettingsService
from src.services.api_usage_service import ApiUsageService
from src.services.stock_analysis_service import StockAnalysisService
from src.services.backtest_service import BacktestService
from src.services.mysql_sync_service import MySqlSyncService
from src.services.dashboard_service import DashboardService
from src.services.feature_engineering_service import FeatureEngineeringService
from src.services.import_service import ImportService
from src.services.analysis_service import AnalysisService
from src.services.scoring_service import ScoringService
from src.services.prediction_model_service import PredictionModelService
from src.services.preference_scoring_service import PreferenceScoringService
from src.services.stock_import_service import StockImportService
from src.services.watchlist_service import WatchlistService
from src.services.trade_republic_universe_service import (
    TradeRepublicUniverseIngestionService,
    TradeRepublicUniverseMatchingService,
)
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)

class ServiceFactory:
    """Zentraler Ort zum Erstellen von Services als Instanzen (Dependency Injection Container)."""

    last_import_issue: str | None = None

    def __init__(self, settings: AppSettings, mysql_client: MySqlClient | None, mongo_wrapper: MongoClientWrapper | None):
        self.settings = settings
        self.mysql_client = mysql_client
        self.mongo_wrapper = mongo_wrapper
        self._mysql_schema_checked_for_import = False
        
        # Cache für Singleton-Services innerhalb der Factory-Lebensdauer
        self._app_settings_service = None
        self._api_usage_service = None
        self._scoring_service = None
        self._gate_evaluator = None
        self._dashboard_service = None
        self._watchlist_service = None
        self._stock_analysis_service = None
        self._stock_import_service = None
        self._feature_engineering_service = None
        self._prediction_model_service = None
        self._backtest_service = None
        self._preference_scoring_service = None
        self._analysis_service = None
        self._analysis_service_key = None
        self._import_service = None
        self._import_service_key = None

    def _ensure_mysql_schema_for_import(self) -> bool:
        if not self.mysql_client:
            return False
        if self._mysql_schema_checked_for_import:
            return True

        try:
            actions = self.mysql_client.initialize_schema()
            if actions:
                LOGGER.info(
                    "ServiceFactory: MySQL schema migration before import applied %s changes.",
                    len(actions),
                )
            self._mysql_schema_checked_for_import = True
            return True
        except Exception as exc:
            ServiceFactory.last_import_issue = (
                "ImportService deaktiviert: MySQL-Schema-Migration fehlgeschlagen "
                f"({exc})."
            )
            LOGGER.warning("ServiceFactory: %s", ServiceFactory.last_import_issue)
            return False

    def create_app_settings_service(self) -> AppSettingsService:
        if self._app_settings_service is None:
            mysql_usable = bool(
                self.mysql_client
                and (hasattr(self.mysql_client, "get_connection") or hasattr(self.mysql_client, "connection"))
            )
            if not mysql_usable and self.mysql_client is not None:
                LOGGER.warning("ServiceFactory: MySQL-Client ist fuer Settings-Repositories nicht nutzbar. Verwende Defaults.")
            filter_repo = AppFilterSettingsRepository(self.mysql_client) if mysql_usable else None
            runtime_repo = AppRuntimePreferencesRepository(self.mysql_client) if mysql_usable else None
            self._app_settings_service = AppSettingsService(runtime_repo, filter_repo, self.settings)
        return self._app_settings_service

    def create_api_usage_service(self) -> ApiUsageService:
        if self._api_usage_service is None:
            repo = ApiUsageRepository(self.mysql_client) if self.mysql_client else None
            self._api_usage_service = ApiUsageService(repo)
        return self._api_usage_service

    def create_scoring_service(self) -> ScoringService:
        if self._scoring_service is None:
            policy = self.create_app_settings_service().load_score_gate_policy()
            self._scoring_service = ScoringService(policy)
        return self._scoring_service

    def create_gate_evaluator(self) -> GateEvaluator:
        if self._gate_evaluator is None:
            policy = self.create_app_settings_service().load_score_gate_policy()
            self._gate_evaluator = GateEvaluator(
                GateRules(
                    min_trade_value=int(policy.gate_min_trade_value),
                    allowed_acquisition_or_disposition=tuple(policy.gate_allowed_acquisition_or_disposition),
                    excluded_transaction_types=tuple(policy.gate_excluded_transaction_types),
                    required_form_type=policy.gate_form_type_required,
                    required_validation_status=policy.gate_validation_status_required,
                )
            )
        return self._gate_evaluator

    def create_dashboard_service(self) -> DashboardService | None:
        if not self.mysql_client:
            return None

        if self._dashboard_service is not None:
            return self._dashboard_service

        raw_repo = None
        company_mongo_repo = None
        if self.mongo_wrapper:
            try:
                raw_repo = InsiderTradeMongoRepository(self.mongo_wrapper)
                company_mongo_repo = CompanyMongoRepository(self.mongo_wrapper)
            except Exception as exc:
                LOGGER.warning(
                    "ServiceFactory: DashboardService startet ohne Mongo-Repositories (degraded mode): %s",
                    exc,
                )

        trade_repo = InsiderTradeMySqlRepository(self.mysql_client)
        company_repo = CompanyMySqlRepository(self.mysql_client)

        self._dashboard_service = DashboardService(
            raw_repo,
            company_mongo_repo,
            trade_repo,
            company_repo,
            preference_score_repo=PreferenceScoreRepository(self.mysql_client),
            watchlist_repo=WatchlistRepository(self.mysql_client),
            data_quality_repo=DataQualityRepository(self.mysql_client),
        )
        return self._dashboard_service

    def create_watchlist_service(self) -> WatchlistService | None:
        if self._watchlist_service is not None:
            return self._watchlist_service
        if not self.mysql_client:
            return None
        repo = WatchlistRepository(self.mysql_client)
        self._watchlist_service = WatchlistService(repo)
        return self._watchlist_service

    def create_stock_analysis_service(self) -> StockAnalysisService | None:
        if self._stock_analysis_service is not None:
            return self._stock_analysis_service
        if not self.mysql_client:
            return None
        watchlist_repo = WatchlistRepository(self.mysql_client)
        data_quality_repo = DataQualityRepository(self.mysql_client)
        self._stock_analysis_service = StockAnalysisService(
            watchlist_repo,
            data_quality_repo,
            company_repository=CompanyMySqlRepository(self.mysql_client),
            price_repository=StockPriceRepository(self.mysql_client),
            technical_feature_repository=TechnicalFeatureRepository(self.mysql_client),
            fundamental_feature_repository=FundamentalFeatureRepository(self.mysql_client),
            prediction_repository=PredictionRepository(self.mysql_client),
            preference_repository=PreferenceScoreRepository(self.mysql_client),
        )
        return self._stock_analysis_service

    def create_prediction_repository(self) -> PredictionRepository | None:
        return PredictionRepository(self.mysql_client) if self.mysql_client else None

    def create_backtest_repository(self) -> BacktestRepository | None:
        return BacktestRepository(self.mysql_client) if self.mysql_client else None

    def create_stock_import_service(self) -> StockImportService | None:
        if self._stock_import_service is not None:
            return self._stock_import_service
        if not self.mysql_client:
            ServiceFactory.last_import_issue = "StockImportService deaktiviert: MySQL-Client fehlt."
            LOGGER.warning("ServiceFactory: %s", ServiceFactory.last_import_issue)
            return None
        if not self.mongo_wrapper:
            ServiceFactory.last_import_issue = "StockImportService deaktiviert: Mongo-Client fehlt (raw provider responses nicht verfuegbar)."
            LOGGER.warning("ServiceFactory: %s", ServiceFactory.last_import_issue)
            return None
        if not self._ensure_mysql_schema_for_import():
            return None
        try:
            fmp_client = FmpClient(
                self.settings.fmp,
                api_usage_service=self.create_api_usage_service(),
            )
            raw_repo = RawProviderResponseMongoRepository(self.mongo_wrapper)
        except Exception as exc:
            ServiceFactory.last_import_issue = f"StockImportService deaktiviert: {exc}"
            LOGGER.warning("ServiceFactory: %s", ServiceFactory.last_import_issue)
            return None

        self._stock_import_service = StockImportService(
            fmp_client=fmp_client,
            raw_repository=raw_repo,
            company_repository=CompanyMySqlRepository(self.mysql_client),
            price_repository=StockPriceRepository(self.mysql_client),
            metrics_repository=FundamentalMetricsRepository(self.mysql_client),
            import_run_repository=ImportRunRepository(self.mysql_client),
            data_quality_repository=DataQualityRepository(self.mysql_client),
        )
        ServiceFactory.last_import_issue = None
        return self._stock_import_service

    def create_feature_engineering_service(self) -> FeatureEngineeringService | None:
        if self._feature_engineering_service is not None:
            return self._feature_engineering_service
        if not self.mysql_client:
            return None
        self._feature_engineering_service = FeatureEngineeringService(
            price_repository=StockPriceRepository(self.mysql_client),
            metrics_repository=FundamentalMetricsRepository(self.mysql_client),
            technical_feature_repository=TechnicalFeatureRepository(self.mysql_client),
            fundamental_feature_repository=FundamentalFeatureRepository(self.mysql_client),
            watchlist_repository=WatchlistRepository(self.mysql_client),
            data_quality_repository=DataQualityRepository(self.mysql_client),
        )
        return self._feature_engineering_service

    def create_prediction_model_service(self) -> PredictionModelService | None:
        if self._prediction_model_service is not None:
            return self._prediction_model_service
        if not self.mysql_client:
            return None
        self._prediction_model_service = PredictionModelService(
            prediction_repository=PredictionRepository(self.mysql_client),
            technical_feature_repository=TechnicalFeatureRepository(self.mysql_client),
            fundamental_feature_repository=FundamentalFeatureRepository(self.mysql_client),
            watchlist_repository=WatchlistRepository(self.mysql_client),
            data_quality_repository=DataQualityRepository(self.mysql_client),
        )
        return self._prediction_model_service

    def create_backtest_service(self) -> BacktestService | None:
        if self._backtest_service is not None:
            return self._backtest_service
        if not self.mysql_client:
            return None
        self._backtest_service = BacktestService(
            prediction_repository=PredictionRepository(self.mysql_client),
            price_repository=StockPriceRepository(self.mysql_client),
            backtest_repository=BacktestRepository(self.mysql_client),
        )
        return self._backtest_service

    def create_preference_scoring_service(self) -> PreferenceScoringService | None:
        if self._preference_scoring_service is not None:
            return self._preference_scoring_service
        if not self.mysql_client:
            return None
        self._preference_scoring_service = PreferenceScoringService(
            preference_repository=PreferenceScoreRepository(self.mysql_client),
            technical_feature_repository=TechnicalFeatureRepository(self.mysql_client),
            fundamental_feature_repository=FundamentalFeatureRepository(self.mysql_client),
            prediction_repository=PredictionRepository(self.mysql_client),
            watchlist_repository=WatchlistRepository(self.mysql_client),
        )
        return self._preference_scoring_service

    def create_analysis_service(self) -> AnalysisService | None:
        if not self.mysql_client:
            return None

        runtime_settings = self.create_app_settings_service().load()
        policy = self.create_app_settings_service().load_score_gate_policy()
        analysis_key = (
            int(policy.score_threshold_pass_min),
            int(policy.score_threshold_hold_min),
            str(runtime_settings.lookup_mode),
            int(runtime_settings.profile_ttl_days),
        )
        if self._analysis_service is not None and self._analysis_service_key == analysis_key:
            return self._analysis_service

        trade_repo = InsiderTradeMySqlRepository(self.mysql_client)
        company_repo = CompanyMySqlRepository(self.mysql_client)

        # FMP Client
        fmp_client = FmpClient(
            replace(
                self.settings.fmp,
                profile_ttl_days=runtime_settings.profile_ttl_days,
                lookup_mode=runtime_settings.lookup_mode,
            ),
            api_usage_service=self.create_api_usage_service()
        )
        
        self._analysis_service = AnalysisService(
            trade_repo,
            company_repo,
            score_gate_policy=policy,
            fmp_client=fmp_client,
            scoring_service=self.create_scoring_service()
        )
        self._analysis_service_key = analysis_key
        return self._analysis_service

    def create_import_service(self) -> ImportService | None:
        # Requirement 9: Kein Betrieb ohne Kernkomponenten (MySQL + Mongo fuer raw+clean Pipeline Pflicht)
        if not self.mysql_client:
            ServiceFactory.last_import_issue = "ImportService deaktiviert: MySQL-Client fehlt."
            LOGGER.warning("ServiceFactory: %s", ServiceFactory.last_import_issue)
            return None

        if not self.mongo_wrapper:
            ServiceFactory.last_import_issue = "ImportService deaktiviert: Mongo-Client fehlt (raw pipeline nicht verfuegbar)."
            LOGGER.warning("ServiceFactory: %s", ServiceFactory.last_import_issue)
            return None

        if not self._ensure_mysql_schema_for_import():
            return None

        trade_repo = InsiderTradeMySqlRepository(self.mysql_client)
        company_repo = CompanyMySqlRepository(self.mysql_client)
        try:
            raw_repo = InsiderTradeMongoRepository(self.mongo_wrapper)
            company_mongo_repo = CompanyMongoRepository(self.mongo_wrapper)
        except Exception as exc:
            ServiceFactory.last_import_issue = f"Mongo nicht erreichbar: {exc}"
            LOGGER.warning("ServiceFactory: ImportService deaktiviert. %s", ServiceFactory.last_import_issue)
            return None
        
        runtime_settings = self.create_app_settings_service().load()
        import_key = (
            tuple(runtime_settings.profile_gate_filter_statuses),
            str(runtime_settings.api2_firing_mode),
            int(runtime_settings.profile_ttl_days),
            str(runtime_settings.lookup_mode),
            bool(self.settings.review_mode or self.settings.disable_import),
        )
        if self._import_service is not None and self._import_service_key == import_key:
            return self._import_service

        try:
            fmp_client = FmpClient(
                replace(
                    self.settings.fmp,
                    profile_ttl_days=runtime_settings.profile_ttl_days,
                    lookup_mode=runtime_settings.lookup_mode,
                ),
                api_usage_service=self.create_api_usage_service()
            )
        except Exception as exc:
            ServiceFactory.last_import_issue = f"FMP-Konfiguration ungueltig: {exc}"
            LOGGER.warning("ServiceFactory: ImportService deaktiviert. %s", ServiceFactory.last_import_issue)
            return None
        
        # Optionale Enrichment-Provider (Alpha Vantage, Polygon) – nur wenn API-Key gesetzt.
        # Diese Provider sind KEIN MVP-Kern. FMP ist der primäre Datenprovider.
        av_key = self.settings.enrichment.alpha_vantage_api_key if hasattr(self.settings, "enrichment") else None
        poly_key = self.settings.enrichment.polygon_api_key if hasattr(self.settings, "enrichment") else None
        av_client = AlphaVantageClient(av_key) if av_key else None
        poly_client = PolygonClient(poly_key) if poly_key else None
        enrichment_service = CompanyEnrichmentService(fmp_client, av_client, poly_client)
        ServiceFactory.last_import_issue = None

        self._import_service = ImportService(
            fmp_client=fmp_client,
            gate_evaluator=self.create_gate_evaluator(),
            raw_repo=raw_repo,
            company_mongo_repo=company_mongo_repo,
            trade_mysql_repo=trade_repo,
            company_mysql_repo=company_repo,
            profile_fetch_statuses=runtime_settings.profile_gate_filter_statuses,
            api2_firing_mode=runtime_settings.api2_firing_mode,
            allow_write=not (self.settings.review_mode or self.settings.disable_import),
            tr_ingestion_service=TradeRepublicUniverseIngestionService(self.settings, self.mysql_client),
            tr_matching_service=TradeRepublicUniverseMatchingService(self.mysql_client),
            enrichment_service=enrichment_service,
            scoring_service=self.create_scoring_service()
        )
        self._import_service_key = import_key
        return self._import_service

    def create_company_repository(self) -> CompanyMySqlRepository | None:
        if not self.mysql_client:
            return None
        return CompanyMySqlRepository(self.mysql_client)

    def create_mysql_sync_service(self) -> MySqlSyncService:
        return MySqlSyncService()
