"""Zentrale Konfiguration für Mercator.

Dieses Modul lädt Umgebungsvariablen und stellt typsichere Settings bereit.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

FMP_BASE_URL = "https://financialmodelingprep.com/stable"
LATEST_INSIDER_ENDPOINT = "/insider-trading/latest"
PROFILE_ENDPOINT = "/profile"
DEFAULT_FEED_PAGE = 0
DEFAULT_FEED_LIMIT = 100
PROFILE_TTL_DAYS = 7
POLL_INTERVAL_HOURS = 1


class SettingsError(ValueError):
    """Fehlerklasse für unvollständige oder ungültige Settings."""



def _read_required_string_env(name: str) -> str:
    """Liest einen Pflichtwert als String aus der Umgebung.

    Args:
        name: Name der Umgebungsvariable.

    Returns:
        Der nicht-leere Umgebungswert.

    Raises:
        SettingsError: Wenn die Variable fehlt oder leer ist.
    """

    value = os.getenv(name)
    if value is None or not value.strip():
        raise SettingsError(
            f"Missing required environment variable '{name}'. "
            "Please set it in your .env file."
        )
    return value.strip()



def _read_int_env(name: str, default: int | None = None) -> int:
    """Liest einen Integer-Wert aus der Umgebung.

    Args:
        name: Name der Umgebungsvariable.
        default: Optionaler Fallback, falls kein Wert gesetzt ist.

    Returns:
        Der geparste Integer-Wert.

    Raises:
        SettingsError: Wenn der Wert fehlt und kein Default existiert oder kein Integer ist.
    """

    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        if default is None:
            raise SettingsError(
                f"Missing required integer environment variable '{name}'."
            )
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise SettingsError(
            f"Environment variable '{name}' must be an integer, got '{raw_value}'."
        ) from exc



def _read_bool_env(name: str, default: bool | None = None) -> bool:
    """Liest einen booleschen Wert aus der Umgebung.

    Args:
        name: Name der Umgebungsvariable.
        default: Optionaler Fallback, falls kein Wert gesetzt ist.

    Returns:
        Der geparste boolesche Wert.

    Raises:
        SettingsError: Wenn der Wert fehlt und kein Default existiert oder ungültig ist.
    """

    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        if default is None:
            raise SettingsError(
                f"Missing required boolean environment variable '{name}'."
            )
        return default

    normalized = raw_value.strip().lower()
    truthy_values = {"1", "true", "yes", "on"}
    falsy_values = {"0", "false", "no", "off"}

    if normalized in truthy_values:
        return True
    if normalized in falsy_values:
        return False

    raise SettingsError(
        f"Environment variable '{name}' must be a boolean value (true/false), got '{raw_value}'."
    )


@dataclass(frozen=True)
class Settings:
    """Zentrale MySQL-Einstellungen für Verbindung und SSL-Verhalten."""

    mysql_host: str
    mysql_port: int
    mysql_database: str
    mysql_user: str
    mysql_password: str
    mysql_connect_timeout: int
    mysql_create_database: bool
    mysql_ssl_disabled: bool
    mysql_ssl_ca: str | None
    mysql_ssl_cert: str | None
    mysql_ssl_key: str | None

    @classmethod
    def from_env(cls) -> Settings:
        """Erstellt Settings aus den geladenen Umgebungsvariablen.

        Returns:
            Eine validierte Settings-Instanz.
        """

        return cls(
            mysql_host=_read_required_string_env("MYSQL_HOST"),
            mysql_port=_read_int_env("MYSQL_PORT", default=3306),
            mysql_database=_read_required_string_env("MYSQL_DATABASE"),
            mysql_user=_read_required_string_env("MYSQL_USER"),
            mysql_password=_read_required_string_env("MYSQL_PASSWORD"),
            mysql_connect_timeout=_read_int_env("MYSQL_CONNECT_TIMEOUT", default=10),
            mysql_create_database=_read_bool_env("MYSQL_CREATE_DATABASE", default=False),
            mysql_ssl_disabled=_read_bool_env("MYSQL_SSL_DISABLED", default=True),
            mysql_ssl_ca=os.getenv("MYSQL_SSL_CA") or None,
            mysql_ssl_cert=os.getenv("MYSQL_SSL_CERT") or None,
            mysql_ssl_key=os.getenv("MYSQL_SSL_KEY") or None,
        )

    def mysql_connection_kwargs(self, include_database: bool = True) -> dict[str, Any]:
        """Erstellt mysql-connector-kompatible Verbindungsparameter.

        Args:
            include_database: Steuert, ob das Schema in den Verbindungsdaten enthalten ist.

        Returns:
            Ein Dictionary für ``mysql.connector.connect(...)``.
        """

        connection_kwargs: dict[str, Any] = {
            "host": self.mysql_host,
            "port": self.mysql_port,
            "user": self.mysql_user,
            "password": self.mysql_password,
            "connection_timeout": self.mysql_connect_timeout,
        }

        if include_database:
            connection_kwargs["database"] = self.mysql_database

        if self.mysql_ssl_disabled:
            connection_kwargs["ssl_disabled"] = True
        else:
            if self.mysql_ssl_ca:
                connection_kwargs["ssl_ca"] = self.mysql_ssl_ca
            if self.mysql_ssl_cert:
                connection_kwargs["ssl_cert"] = self.mysql_ssl_cert
            if self.mysql_ssl_key:
                connection_kwargs["ssl_key"] = self.mysql_ssl_key

        return connection_kwargs


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
    mysql: Settings
    mongo: MongoConfig
    fmp: FmpConfig


def load_settings() -> AppSettings:
    """Lädt die vollständigen Anwendungseinstellungen aus der Umgebung.

    Returns:
        Vollständige AppSettings inklusive Datenbank- und API-Konfiguration.
    """

    project_root = Path(__file__).resolve().parents[2]
    return AppSettings(
        app_env=os.getenv("APP_ENV", "local"),
        app_title=os.getenv("APP_TITLE", "Mercator"),
        dataset_path=os.getenv("DATASET_PATH", "data/raw/"),
        project_root=project_root,
        mysql=Settings.from_env(),
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


# TODO: Prüfen, ob die Uni-MySQL-Instanz SSL zwingend voraussetzt und welche Zertifikatspfade nötig sind.
# TODO: Echte Uni-Zugangsdaten (Host, User, Passwort) pro Umgebung in .env hinterlegen.
