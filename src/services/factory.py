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
)
from src.db.mysql_client import MySqlClient
from src.db.repositories.company_repository import CompanyMySqlRepository
from src.db.repositories.trade_repository import InsiderTradeMySqlRepository
from src.db.repositories.settings_repository import (
    AppFilterSettingsRepository,
    AppRuntimePreferencesRepository,
)
from src.db.repositories.api_usage_repository import ApiUsageRepository
from src.preprocessing import GateEvaluator, GateRules
from src.services.app_settings_service import AppSettingsService
from src.services.api_usage_service import ApiUsageService
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService
from src.services.analysis_service import AnalysisService
from src.services.scoring_service import ScoringService
from src.services.trade_republic_universe_service import (
    TradeRepublicUniverseIngestionService,
    TradeRepublicUniverseMatchingService,
)
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)

class ServiceFactory:
    """Zentraler Ort zum Erstellen von Services als Instanzen (Dependency Injection Container)."""

    def __init__(self, settings: AppSettings, mysql_client: MySqlClient | None, mongo_wrapper: MongoClientWrapper | None):
        self.settings = settings
        self.mysql_client = mysql_client
        self.mongo_wrapper = mongo_wrapper
        
        # Cache für Singleton-Services innerhalb der Factory-Lebensdauer
        self._app_settings_service = None
        self._api_usage_service = None
        self._scoring_service = None
        self._gate_evaluator = None

    def create_app_settings_service(self) -> AppSettingsService:
        if self._app_settings_service is None:
            filter_repo = AppFilterSettingsRepository(self.mysql_client) if self.mysql_client else None
            runtime_repo = AppRuntimePreferencesRepository(self.mysql_client) if self.mysql_client else None
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
                    required_security_name=policy.gate_security_name_required,
                    required_validation_status=policy.gate_validation_status_required,
                )
            )
        return self._gate_evaluator

    def create_dashboard_service(self) -> DashboardService | None:
        if not self.mysql_client:
            return None
        
        raw_repo = InsiderTradeMongoRepository(self.mongo_wrapper) if self.mongo_wrapper else None
        company_mongo_repo = CompanyMongoRepository(self.mongo_wrapper) if self.mongo_wrapper else None
        trade_repo = InsiderTradeMySqlRepository(self.mysql_client)
        company_repo = CompanyMySqlRepository(self.mysql_client)
        
        return DashboardService(raw_repo, company_mongo_repo, trade_repo, company_repo)

    def create_analysis_service(self) -> AnalysisService | None:
        if not self.mysql_client:
            return None
        
        trade_repo = InsiderTradeMySqlRepository(self.mysql_client)
        company_repo = CompanyMySqlRepository(self.mysql_client)
        policy = self.create_app_settings_service().load_score_gate_policy()
        
        # FMP Client
        runtime_settings = self.create_app_settings_service().load()
        fmp_client = FmpClient(
            replace(
                self.settings.fmp,
                profile_ttl_days=runtime_settings.profile_ttl_days,
                lookup_mode=runtime_settings.lookup_mode,
            ),
            api_usage_service=self.create_api_usage_service()
        )
        
        return AnalysisService(
            trade_repo,
            company_repo,
            score_gate_policy=policy,
            fmp_client=fmp_client,
            scoring_service=self.create_scoring_service()
        )

    def create_import_service(self) -> ImportService | None:
        # Requirement 9: Kein Betrieb ohne Kernkomponenten (MySQL hier Pflicht fuer vollen Import)
        if not self.mysql_client or not self.mongo_wrapper:
            LOGGER.warning("ServiceFactory: ImportService nicht moeglich (DB fehlt).")
            return None
            
        trade_repo = InsiderTradeMySqlRepository(self.mysql_client)
        company_repo = CompanyMySqlRepository(self.mysql_client)
        raw_repo = InsiderTradeMongoRepository(self.mongo_wrapper)
        company_mongo_repo = CompanyMongoRepository(self.mongo_wrapper)
        
        runtime_settings = self.create_app_settings_service().load()
        fmp_client = FmpClient(
            replace(
                self.settings.fmp,
                profile_ttl_days=runtime_settings.profile_ttl_days,
                lookup_mode=runtime_settings.lookup_mode,
            ),
            api_usage_service=self.create_api_usage_service()
        )
        
        # Enrichment Service
        av_client = AlphaVantageClient(self.settings.enrichment.alpha_vantage_api_key) if self.settings.enrichment.alpha_vantage_api_key else None
        poly_client = PolygonClient(self.settings.enrichment.polygon_api_key) if self.settings.enrichment.polygon_api_key else None
        enrichment_service = CompanyEnrichmentService(fmp_client, av_client, poly_client)

        return ImportService(
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

    def create_company_repository(self) -> CompanyMySqlRepository | None:
        if not self.mysql_client:
            return None
        return CompanyMySqlRepository(self.mysql_client)
