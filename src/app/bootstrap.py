"""Bootstrap-Logik für Mercator (Requirement 5.1)."""

from __future__ import annotations
import streamlit as st
from src.config.settings import AppSettings, load_settings
from src.db.mongo_client import MongoClientWrapper
from src.db.mysql_client_factory import build_mysql_client_for_target
from src.db.mysql_target_resolver import MySqlResolutionResult
from src.services.database_status_service import DatabaseStatus, DatabaseStatusService
from src.services.app_settings_service import AppSettingsService
from src.services.factory import ServiceFactory
from src.ui.ui_theme import apply_ui_theme

MYSQL_TARGET_STATE_KEY = "mysql_runtime_target"

def bootstrap_app():
    """Initialisiert die App, konfiguriert Streamlit und baut die Services auf."""
    st.set_page_config(
        page_title="Mercator | Insider Intelligence",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Theme anwenden
    apply_ui_theme()
    
    # Einstellungen laden
    settings = load_settings()
    
    # DB Status & Service Aufbau
    db_status, mysql_res, factory = _init_core_services(settings)
    
    return settings, db_status, mysql_res, factory

def _init_core_services(settings: AppSettings):
    """Initialisiert Datenbankverbindungen und die Service-Factory."""
    # Ziel-Resolver
    requested_target = st.session_state.get(MYSQL_TARGET_STATE_KEY, settings.mysql.mysql_active_target)
    
    status_service = DatabaseStatusService()
    mongo_wrapper = MongoClientWrapper(settings.mongo)
    
    db_status, mysql_res = status_service.evaluate(
        mysql_settings=settings.mysql,
        mongo_client=mongo_wrapper,
        requested_target=requested_target
    )
    
    # MySQL Client
    mysql_client = None
    if mysql_res and mysql_res.active_target:
        mysql_client = build_mysql_client_for_target(settings.mysql, mysql_res.active_target)
        
    # Factory
    factory = ServiceFactory(
        settings=settings,
        mysql_client=mysql_client,
        mongo_wrapper=mongo_wrapper
    )
    
    return db_status, mysql_res, factory
