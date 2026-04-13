from __future__ import annotations
from dataclasses import replace

from src.config.settings import AppSettings
from src.data_sources.fmp_client import FmpClient
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
)
from src.preprocessing import GateEvaluator, GateRules
from src.services.app_settings_service import AppSettingsService
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService
from src.services.analysis_service import AnalysisService
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)

class ServiceFactory:
    """Zentraler Ort zum Erstellen von Services, um Duplikate zwischen UI und API zu vermeiden."""

    last_import_issue: str | None = None

    @staticmethod
    def build_all(settings: AppSettings, mysql_client: MySqlClient, mongo_available: bool = True) -> tuple[
        DashboardService, AnalysisService, ImportService | None, AppSettingsService
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

        # Services
        runtime_settings_service = AppSettingsService(runtime_settings_repo, filter_repo, settings)
        runtime_settings = runtime_settings_service.load()

        gate_evaluator = GateEvaluator(GateRules())

        import_service: ImportService | None = None
        if mongo_client is not None and raw_repo is not None and company_mongo_repo is not None:
            try:
                fmp_client = FmpClient(
                    replace(
                        settings.fmp,
                        profile_ttl_days=runtime_settings.profile_ttl_days,
                        lookup_mode=runtime_settings.lookup_mode,
                    )
                )
                import_service = ImportService(
                    fmp_client=fmp_client,
                    gate_evaluator=gate_evaluator,
                    raw_repo=raw_repo,
                    company_mongo_repo=company_mongo_repo,
                    trade_mysql_repo=trade_repo,
                    company_mysql_repo=company_repo,
                    profile_fetch_statuses=runtime_settings.profile_gate_filter_statuses,
                    allow_write=not (settings.review_mode or settings.disable_import),
                )
            except ValueError as exc:
                ServiceFactory.last_import_issue = (
                    f"FMP-Konfiguration ungueltig ({settings.fmp.api_key_source}): {exc}"
                )
                LOGGER.warning("ServiceFactory: ImportService deaktiviert (%s)", ServiceFactory.last_import_issue)
            except Exception as exc:
                ServiceFactory.last_import_issue = f"FMP-Client Initialisierung fehlgeschlagen: {exc}"
                LOGGER.error("ServiceFactory: ImportService deaktiviert (%s)", ServiceFactory.last_import_issue)
        else:
            if ServiceFactory.last_import_issue is None:
                ServiceFactory.last_import_issue = "MongoDB nicht verfuegbar."
            LOGGER.warning("ServiceFactory: ImportService deaktiviert (%s)", ServiceFactory.last_import_issue)

        dashboard_service = DashboardService(raw_repo, company_mongo_repo, trade_repo, company_repo)
        analysis_service = AnalysisService(trade_repo, company_repo)
        
        return dashboard_service, analysis_service, import_service, runtime_settings_service

    @staticmethod
    def build_ingestion_only(settings: AppSettings) -> tuple[ImportService | None, AppSettingsService]:
        """Erstellt Services für den Fall 'Mongo erreichbar, MySQL nicht erreichbar'."""

        ServiceFactory.last_import_issue = None

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

        gate_evaluator = GateEvaluator(GateRules())

        try:
            fmp_client = FmpClient(
                replace(
                    settings.fmp,
                    profile_ttl_days=runtime_settings.profile_ttl_days,
                    lookup_mode=runtime_settings.lookup_mode,
                )
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
            )
        except ValueError as exc:
            import_service = None
            ServiceFactory.last_import_issue = f"FMP-Konfiguration ungueltig ({settings.fmp.api_key_source}): {exc}"
            LOGGER.warning("ServiceFactory: Ingestion-only deaktiviert (%s)", ServiceFactory.last_import_issue)
        except Exception as exc:
            import_service = None
            ServiceFactory.last_import_issue = f"FMP-Client Initialisierung fehlgeschlagen: {exc}"
            LOGGER.error("ServiceFactory: Ingestion-only deaktiviert (%s)", ServiceFactory.last_import_issue)

        if import_service is not None:
            LOGGER.warning("ServiceFactory: Ingestion-only Modus aktiv (MySQL nicht verfuegbar).")
        return import_service, runtime_settings_service

