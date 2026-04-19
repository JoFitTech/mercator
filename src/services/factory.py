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
from src.db.mysql_repository import (
    CompanyMySqlRepository,
    InsiderTradeMySqlRepository,
    AppFilterSettingsRepository,
    AppRuntimePreferencesRepository,
    ApiUsageRepository,
)
from src.preprocessing import GateEvaluator, GateRules
from src.services.app_settings_service import AppSettingsService
from src.services.api_usage_service import ApiUsageService
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService
from src.services.analysis_service import AnalysisService
from src.services.trade_republic_universe_service import (
    TradeRepublicUniverseIngestionService,
    TradeRepublicUniverseMatchingService,
)
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)

class ServiceFactory:
    """Zentraler Ort zum Erstellen von Services, um Duplikate zwischen UI und API zu vermeiden."""

    last_import_issue: str | None = None

    @staticmethod
    def build_all(settings: AppSettings, mysql_client: MySqlClient, mongo_available: bool = True) -> tuple[
        DashboardService, AnalysisService, ImportService | None, AppSettingsService, ApiUsageService
    ]:
        ServiceFactory.last_import_issue = None
        mysql_client.initialize_schema()
        mongo_client = MongoClientWrapper(settings.mongo) if mongo_available else None

        # Repositories
        raw_repo = None
        company_mongo_repo = None
        if mongo_client is not None:
            try:
                raw_repo = InsiderTradeMongoRepository(mongo_client)
                company_mongo_repo = CompanyMongoRepository(mongo_client)
            except Exception as exc:
                LOGGER.error("ServiceFactory: Mongo repository init fehlgeschlagen: %s", exc, exc_info=True)
                ServiceFactory.last_import_issue = (
                    "MongoDB-Daten inkonsistent oder Index fehlerhaft (companies/company_key)."
                )
                LOGGER.warning("ServiceFactory: ImportService deaktiviert (%s).", ServiceFactory.last_import_issue)
                raw_repo = None
                company_mongo_repo = None

        trade_repo = InsiderTradeMySqlRepository(mysql_client)
        company_repo = CompanyMySqlRepository(mysql_client)
        filter_repo = AppFilterSettingsRepository(mysql_client)
        runtime_settings_repo = AppRuntimePreferencesRepository(mysql_client)
        api_usage_repo = ApiUsageRepository(mysql_client)

        # Services
        api_usage_service = ApiUsageService(api_usage_repo)
        runtime_settings_service = AppSettingsService(runtime_settings_repo, filter_repo, settings)
        runtime_settings = runtime_settings_service.load()
        score_gate_policy = runtime_settings_service.load_score_gate_policy()
        gate_evaluator = GateEvaluator(
            GateRules(
                min_trade_value=int(score_gate_policy.gate_min_trade_value),
                allowed_acquisition_or_disposition=tuple(score_gate_policy.gate_allowed_acquisition_or_disposition),
                excluded_transaction_types=tuple(score_gate_policy.gate_excluded_transaction_types),
                required_form_type=score_gate_policy.gate_form_type_required,
                required_security_name=score_gate_policy.gate_security_name_required,
                required_validation_status=score_gate_policy.gate_validation_status_required,
            )
        )

        import_service: ImportService | None = None
        fmp_client: FmpClient | None = None
        if mongo_client is not None and raw_repo is not None and company_mongo_repo is not None:
            try:
                fmp_client = FmpClient(
                    replace(
                        settings.fmp,
                        profile_ttl_days=runtime_settings.profile_ttl_days,
                        lookup_mode=runtime_settings.lookup_mode,
                    ),
                    api_usage_service=api_usage_service
                )
                
                # Enrichment Service vorbereiten
                av_client = None
                if settings.enrichment.alpha_vantage_api_key:
                    av_client = AlphaVantageClient(settings.enrichment.alpha_vantage_api_key)
                
                poly_client = None
                if settings.enrichment.polygon_api_key:
                    poly_client = PolygonClient(settings.enrichment.polygon_api_key)
                    
                enrichment_service = CompanyEnrichmentService(
                    fmp_client=fmp_client,
                    alpha_vantage_client=av_client,
                    polygon_client=poly_client
                )

                import_service = ImportService(
                    fmp_client=fmp_client,
                    gate_evaluator=gate_evaluator,
                    raw_repo=raw_repo,
                    company_mongo_repo=company_mongo_repo,
                    trade_mysql_repo=trade_repo,
                    company_mysql_repo=company_repo,
                    profile_fetch_statuses=runtime_settings.profile_gate_filter_statuses,
                    api2_firing_mode=runtime_settings.api2_firing_mode,
                    allow_write=not (settings.review_mode or settings.disable_import),
                    tr_ingestion_service=TradeRepublicUniverseIngestionService(settings, mysql_client),
                    tr_matching_service=TradeRepublicUniverseMatchingService(mysql_client),
                    enrichment_service=enrichment_service,
                )
            except ValueError as exc:
                ServiceFactory.last_import_issue = (
                    f"FMP-Konfiguration ungueltig ({settings.fmp.api_key_source}):\n{str(exc)}"
                )
                LOGGER.warning("ServiceFactory: ImportService deaktiviert. Reason:\n%s", ServiceFactory.last_import_issue)
            except Exception as exc:
                ServiceFactory.last_import_issue = f"FMP-Client Initialisierung fehlgeschlagen: {exc}"
                LOGGER.error("ServiceFactory: ImportService deaktiviert (%s)", ServiceFactory.last_import_issue)
        else:
            if ServiceFactory.last_import_issue is None:
                ServiceFactory.last_import_issue = "MongoDB nicht verfuegbar."
            LOGGER.warning("ServiceFactory: ImportService deaktiviert (%s)", ServiceFactory.last_import_issue)

        dashboard_service = DashboardService(raw_repo, company_mongo_repo, trade_repo, company_repo)
        analysis_service = AnalysisService(
            trade_repo,
            company_repo,
            score_gate_policy=score_gate_policy,
            fmp_client=fmp_client,
        )
        
        return dashboard_service, analysis_service, import_service, runtime_settings_service, api_usage_service

    @staticmethod
    def build_ingestion_only(settings: AppSettings) -> tuple[ImportService | None, AppSettingsService, ApiUsageService]:
        """Erstellt Services für den Fall 'Mongo erreichbar, MySQL nicht erreichbar'."""

        ServiceFactory.last_import_issue = None
        api_usage_service = ApiUsageService(None)

        mongo_client = MongoClientWrapper(settings.mongo)
        try:
            raw_repo = InsiderTradeMongoRepository(mongo_client)
            company_mongo_repo = CompanyMongoRepository(mongo_client)
        except Exception as exc:
            LOGGER.error("ServiceFactory: Ingestion-only Mongo init fehlgeschlagen: %s", exc, exc_info=True)
            runtime_settings_service = AppSettingsService(runtime_repo=None, filter_repo=None, defaults=settings)
            ServiceFactory.last_import_issue = "MongoDB-Daten inkonsistent oder Index fehlerhaft (companies/company_key)."
            LOGGER.warning("ServiceFactory: Ingestion-only deaktiviert (%s)", ServiceFactory.last_import_issue)
            return None, runtime_settings_service

        runtime_settings_service = AppSettingsService(runtime_repo=None, filter_repo=None, defaults=settings)
        runtime_settings = runtime_settings_service.load()

        score_gate_policy = runtime_settings_service.load_score_gate_policy()
        gate_evaluator = GateEvaluator(
            GateRules(
                min_trade_value=int(score_gate_policy.gate_min_trade_value),
                allowed_acquisition_or_disposition=tuple(score_gate_policy.gate_allowed_acquisition_or_disposition),
                excluded_transaction_types=tuple(score_gate_policy.gate_excluded_transaction_types),
                required_form_type=score_gate_policy.gate_form_type_required,
                required_security_name=score_gate_policy.gate_security_name_required,
                required_validation_status=score_gate_policy.gate_validation_status_required,
            )
        )

        try:
            fmp_client = FmpClient(
                replace(
                    settings.fmp,
                    profile_ttl_days=runtime_settings.profile_ttl_days,
                    lookup_mode=runtime_settings.lookup_mode,
                ),
                api_usage_service=api_usage_service
            )
            
            # Enrichment Service vorbereiten
            av_client = None
            if settings.enrichment.alpha_vantage_api_key:
                av_client = AlphaVantageClient(settings.enrichment.alpha_vantage_api_key)
            
            poly_client = None
            if settings.enrichment.polygon_api_key:
                poly_client = PolygonClient(settings.enrichment.polygon_api_key)
                
            enrichment_service = CompanyEnrichmentService(
                fmp_client=fmp_client,
                alpha_vantage_client=av_client,
                polygon_client=poly_client
            )

            import_service = ImportService(
                fmp_client=fmp_client,
                gate_evaluator=gate_evaluator,
                raw_repo=raw_repo,
                company_mongo_repo=company_mongo_repo,
                trade_mysql_repo=None,
                company_mysql_repo=None,
                profile_fetch_statuses=runtime_settings.profile_gate_filter_statuses,
                allow_write=not (settings.review_mode or settings.disable_import),
                enrichment_service=enrichment_service,
            )
        except ValueError as exc:
            import_service = None
            ServiceFactory.last_import_issue = f"FMP-Konfiguration ungueltig ({settings.fmp.api_key_source}):\n{str(exc)}"
            LOGGER.warning("ServiceFactory: Ingestion-only deaktiviert. Reason:\n%s", ServiceFactory.last_import_issue)
        except Exception as exc:
            import_service = None
            ServiceFactory.last_import_issue = f"FMP-Client Initialisierung fehlgeschlagen: {exc}"
            LOGGER.error("ServiceFactory: Ingestion-only deaktiviert (%s)", ServiceFactory.last_import_issue)

        if import_service is not None:
            LOGGER.warning("ServiceFactory: Ingestion-only Modus aktiv (MySQL nicht verfuegbar).")
        return import_service, runtime_settings_service, api_usage_service
