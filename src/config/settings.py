"""Zentrale Konfiguration für Mercator.

Dieses Modul kapselt Umgebungsvariablen für API, Datenbanken und App-Metadaten.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

FMP_BASE_URL = "https://financialmodelingprep.com/stable"
LATEST_INSIDER_ENDPOINT = "/insider-trading/latest"
PROFILE_ENDPOINT = "/profile"
DEFAULT_FEED_PAGE = 0
DEFAULT_FEED_LIMIT = 100
PROFILE_TTL_DAYS = 7
POLL_INTERVAL_HOURS = 1


@dataclass(frozen=True)
class MySqlConfig:
    """Konfiguration für MySQL-Verbindungen."""

    host: str
    port: int
    database: str
    user: str
    password: str


@dataclass(frozen=True)
class MongoConfig:
    """Konfiguration für MongoDB-Verbindungen."""

    uri: str
    database: str


@dataclass(frozen=True)
class FmpConfig:
    """Konfiguration für den FMP-Zugriff inklusive API-Key."""

    base_url: str
    api_key: str
    default_feed_page: int = DEFAULT_FEED_PAGE
    default_feed_limit: int = DEFAULT_FEED_LIMIT
    profile_ttl_days: int = PROFILE_TTL_DAYS
    poll_interval_hours: int = POLL_INTERVAL_HOURS


@dataclass(frozen=True)
class AppSettings:
    """Zentrale Anwendungseinstellungen für Services und UI."""

    app_env: str
    app_title: str
    dataset_path: str
    project_root: Path
    mysql: MySqlConfig
    mongo: MongoConfig
    fmp: FmpConfig


def load_settings() -> AppSettings:
    """Lädt Settings aus `.env` mit lokalen Entwicklungsdefaults.

    Returns:
        AppSettings: Vollständige Konfiguration für das Projekt.
    """

    project_root = Path(__file__).resolve().parents[2]
    return AppSettings(
        app_env=os.getenv("APP_ENV", "local"),
        app_title=os.getenv("APP_TITLE", "Mercator"),
        dataset_path=os.getenv("DATASET_PATH", "data/raw/"),
        project_root=project_root,
        mysql=MySqlConfig(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            database=os.getenv("MYSQL_DATABASE", "mercator"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "change_me"),
        ),
        mongo=MongoConfig(
            uri=os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
            database=os.getenv("MONGO_DATABASE", "mercator"),
        ),
        fmp=FmpConfig(
            base_url=FMP_BASE_URL,
            api_key=os.getenv("FMP_API_KEY", ""),
        ),
    )


def validate_fmp_api_key(api_key: str) -> None:
    """Validiert den API-Key für Importläufe.

    Args:
        api_key: API-Key aus der Konfiguration.

    Raises:
        ValueError: Falls der Key fehlt oder nur Platzhalter enthält.
    """

    if not api_key or api_key.strip().lower() in {"change_me", "your_api_key"}:
        raise ValueError(
            "FMP_API_KEY fehlt oder ist ein Platzhalter. Bitte trage einen gültigen Schlüssel in der .env ein."
        )
