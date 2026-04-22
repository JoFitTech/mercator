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


@st.cache_resource(show_spinner=False)
def _cached_settings():
    """Einstellungen einmalig laden und cachen (kein Rerun-Overhead)."""
    return load_settings()


@st.cache_resource(ttl=300, show_spinner=False)
def _cached_core_services(requested_target: str):
    """Datenbankverbindungen und Factory einmalig aufbauen und 5 Minuten cachen.

    Der Cache-Key enthält das gewünschte MySQL-Target, damit ein Target-Wechsel
    im Admin-Panel einen echten Neuaufbau auslöst.
    """
    settings = _cached_settings()
    status_service = DatabaseStatusService()
    db_status, mysql_res, mongo_res = status_service.evaluate(
        mysql_settings=settings.mysql,
        mongo_settings=settings.mongo_targets or MongoSettings.from_env(),
        requested_target=requested_target,
    )

    mysql_client = mysql_res.client if (mysql_res and db_status.mysql.is_connected) else None
    mongo_for_factory = mongo_res.client if (mongo_res and db_status.mongo.is_connected) else None

    factory = ServiceFactory(
        settings=settings,
        mysql_client=mysql_client,
        mongo_wrapper=mongo_for_factory,
    )
    return db_status, mysql_res, factory


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

    # Einstellungen aus Cache
    settings = _cached_settings()

    # Ziel-Resolver: Target aus der Session lesen (Admin-Panel kann es wechseln)
    requested_target = st.session_state.get(MYSQL_TARGET_STATE_KEY, settings.mysql.mysql_active_target)

    # DB Status & Service aus Cache holen (nur bei Target-Wechsel oder TTL-Ablauf neu gebaut)
    db_status, mysql_res, factory = _cached_core_services(requested_target)

    return settings, db_status, mysql_res, factory


def invalidate_core_services_cache() -> None:
    """Leert den Service-Cache, z.B. nach einem manuellen Target-Wechsel im Admin."""
    _cached_core_services.clear()


def _init_core_services(settings: AppSettings):
    """Initialisiert Datenbankverbindungen und die Service-Factory.

    .. deprecated::
        Verwende stattdessen :func:`_cached_core_services`. Diese Funktion
        bleibt aus Kompatibilitätsgründen erhalten.
    """
    requested_target = st.session_state.get(MYSQL_TARGET_STATE_KEY, settings.mysql.mysql_active_target)
    return _cached_core_services(requested_target)
