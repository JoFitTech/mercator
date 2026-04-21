"""Bootstrap-Logik für Mercator (Requirement 5.1)."""

from __future__ import annotations
from pathlib import Path

import streamlit as st
from src.config.settings import AppSettings, MongoSettings, load_settings
from src.services.database_status_service import DatabaseStatusService
from src.services.factory import ServiceFactory
from src.ui.ui_theme import apply_ui_theme

MYSQL_TARGET_STATE_KEY = "mysql_runtime_target"


def _resolve_favicon_path() -> str | None:
    """Liefert den FavIcon-Pfad, falls die PNG-Datei vorhanden ist."""

    favicon_path = Path(__file__).resolve().parents[2] / "assets" / "favicon" / "favicon.png"
    return str(favicon_path) if favicon_path.exists() else None

def bootstrap_app():
    """Initialisiert die App, konfiguriert Streamlit und baut die Services auf."""
    page_config: dict[str, str] = {
        "page_title": "Mercator | Insider Intelligence",
        "layout": "wide",
        "initial_sidebar_state": "expanded",
    }
    favicon_path = _resolve_favicon_path()
    if favicon_path:
        page_config["page_icon"] = favicon_path

    st.set_page_config(
        **page_config,
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
    db_status, mysql_res, mongo_res = status_service.evaluate(
        mysql_settings=settings.mysql,
        mongo_settings=settings.mongo_targets or MongoSettings.from_env(),
        requested_target=requested_target
    )
    
    # MySQL Client nur verwenden, wenn die Verbindung durch den Resolver als nutzbar bestätigt wurde
    mysql_client = mysql_res.client if (mysql_res and db_status.mysql.is_connected) else None
        
    # Mongo nur dann an die Factory geben, wenn die Verbindung als nutzbar bewertet wurde.
    mongo_for_factory = mongo_res.client if (mongo_res and db_status.mongo.is_connected) else None

    # Factory
    factory = ServiceFactory(
        settings=settings,
        mysql_client=mysql_client,
        mongo_wrapper=mongo_for_factory
    )
    
    return db_status, mysql_res, factory
