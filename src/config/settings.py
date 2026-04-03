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
DEFAULT_GATE_MIN_TRADE_VALUE = 10_000
ALLOWED_GATE_FILTER_STATUSES = {
    "PASS",
    "PENDING",
    "FAIL",
    "PROFILE_FETCHED",
    "PROFILE_FETCH_FAILED",
}
ALLOWED_MYSQL_TARGETS = {"local", "uni"}


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


def _read_string_env(name: str, default: str = "") -> str:
    """Liest einen Stringwert aus der Umgebung.

    Args:
        name: Name der Umgebungsvariable.
        default: Fallback-Wert bei leerem oder fehlendem Eintrag.

    Returns:
        Den gelesenen oder den Default-String.
    """

    value = os.getenv(name)
    if value is None:
        return default

    stripped = value.strip()
    return stripped if stripped else default


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


def _read_csv_status_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    """Liest eine komma-separierte Statusliste aus der Umgebung und validiert diese."""

    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    statuses = tuple(item.strip().upper() for item in raw_value.split(",") if item.strip())
    if not statuses:
        return default

    invalid = sorted(set(statuses) - ALLOWED_GATE_FILTER_STATUSES)
    if invalid:
        raise SettingsError(
            f"Environment variable '{name}' contains invalid values: {', '.join(invalid)}. "
            f"Allowed values: {', '.join(sorted(ALLOWED_GATE_FILTER_STATUSES))}."
        )

    return statuses


@dataclass(frozen=True)
class MySqlTargetSettings:
    """MySQL-Konfiguration für genau ein Zielsystem."""

    name: str
    host: str
    port: int
    database: str
    user: str
    password: str
    connect_timeout: int
    create_database: bool
    ssl_disabled: bool
    ssl_ca: str | None
    ssl_cert: str | None
    ssl_key: str | None

    def validate_for_connection(self) -> None:
        """Validiert, ob die Pflichtfelder für eine Verbindungsaufnahme gesetzt sind.

        Args:
            Keine.

        Returns:
            None.

        Raises:
            SettingsError: Wenn Host/DB/User/Passwort fehlen.
        """

        missing: list[str] = []
        if not self.host:
            missing.append("host")
        if not self.database:
            missing.append("database")
        if not self.user:
            missing.append("user")
        if not self.password:
            missing.append("password")
        if missing:
            raise SettingsError(
                f"MySQL target '{self.name}' is missing required connection fields: {', '.join(missing)}."
            )

    def mysql_connection_kwargs(self, include_database: bool = True) -> dict[str, Any]:
        """Erstellt mysql-connector-kompatible Verbindungsparameter.

        Args:
            include_database: Steuert, ob das Schema in den Verbindungsdaten enthalten ist.

        Returns:
            Ein Dictionary für ``mysql.connector.connect(...)``.
        """

        self.validate_for_connection()

        connection_kwargs: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "connection_timeout": self.connect_timeout,
        }

        if include_database:
            connection_kwargs["database"] = self.database

        if self.ssl_disabled:
            connection_kwargs["ssl_disabled"] = True
        else:
            if self.ssl_ca:
                connection_kwargs["ssl_ca"] = self.ssl_ca
            if self.ssl_cert:
                connection_kwargs["ssl_cert"] = self.ssl_cert
            if self.ssl_key:
                connection_kwargs["ssl_key"] = self.ssl_key

        return connection_kwargs


@dataclass(frozen=True)
class Settings:
    """Zentrale MySQL-Einstellungen inklusive Target-Auswahl."""

    mysql_active_target: str
    mysql_auto_fallback_to_local: bool
    mysql_sync_enabled: bool
    local_mysql: MySqlTargetSettings
    uni_mysql: MySqlTargetSettings

    @classmethod
    def from_env(cls) -> Settings:
        """Erstellt Settings aus den geladenen Umgebungsvariablen.

        Returns:
            Eine validierte Settings-Instanz.
        """

        active_target = _read_string_env("MYSQL_ACTIVE_TARGET", default="local").lower()
        if active_target not in ALLOWED_MYSQL_TARGETS:
            raise SettingsError(
                "Environment variable 'MYSQL_ACTIVE_TARGET' must be one of: local, uni. "
                f"Got '{active_target}'."
            )

        return cls(
            mysql_active_target=active_target,
            mysql_auto_fallback_to_local=_read_bool_env("MYSQL_AUTO_FALLBACK_TO_LOCAL", default=True),
            mysql_sync_enabled=_read_bool_env("MYSQL_SYNC_ENABLED", default=True),
            local_mysql=MySqlTargetSettings(
                name="local",
                host=_read_string_env("LOCAL_MYSQL_HOST", default=_read_string_env("MYSQL_HOST", default="localhost")),
                port=_read_int_env("LOCAL_MYSQL_PORT", default=_read_int_env("MYSQL_PORT", default=3306)),
                database=_read_string_env(
                    "LOCAL_MYSQL_DATABASE", default=_read_string_env("MYSQL_DATABASE", default="mercator_local")
                ),
                user=_read_string_env("LOCAL_MYSQL_USER", default=_read_string_env("MYSQL_USER", default="root")),
                password=_read_string_env(
                    "LOCAL_MYSQL_PASSWORD", default=_read_string_env("MYSQL_PASSWORD", default="change_me")
                ),
                connect_timeout=_read_int_env(
                    "LOCAL_MYSQL_CONNECT_TIMEOUT", default=_read_int_env("MYSQL_CONNECT_TIMEOUT", default=10)
                ),
                create_database=_read_bool_env(
                    "LOCAL_MYSQL_CREATE_DATABASE", default=_read_bool_env("MYSQL_CREATE_DATABASE", default=False)
                ),
                ssl_disabled=_read_bool_env(
                    "LOCAL_MYSQL_SSL_DISABLED", default=_read_bool_env("MYSQL_SSL_DISABLED", default=True)
                ),
                ssl_ca=os.getenv("LOCAL_MYSQL_SSL_CA") or (os.getenv("MYSQL_SSL_CA") or None),
                ssl_cert=os.getenv("LOCAL_MYSQL_SSL_CERT") or (os.getenv("MYSQL_SSL_CERT") or None),
                ssl_key=os.getenv("LOCAL_MYSQL_SSL_KEY") or (os.getenv("MYSQL_SSL_KEY") or None),
            ),
            uni_mysql=MySqlTargetSettings(
                name="uni",
                host=_read_string_env("UNI_MYSQL_HOST", default=""),
                port=_read_int_env("UNI_MYSQL_PORT", default=3306),
                database=_read_string_env("UNI_MYSQL_DATABASE", default=""),
                user=_read_string_env("UNI_MYSQL_USER", default=""),
                password=_read_string_env("UNI_MYSQL_PASSWORD", default=""),
                connect_timeout=_read_int_env("UNI_MYSQL_CONNECT_TIMEOUT", default=5),
                create_database=_read_bool_env("UNI_MYSQL_CREATE_DATABASE", default=False),
                ssl_disabled=_read_bool_env("UNI_MYSQL_SSL_DISABLED", default=True),
                ssl_ca=os.getenv("UNI_MYSQL_SSL_CA") or None,
                ssl_cert=os.getenv("UNI_MYSQL_SSL_CERT") or None,
                ssl_key=os.getenv("UNI_MYSQL_SSL_KEY") or None,
            ),
        )

    def get_mysql_target(self, name: str) -> MySqlTargetSettings:
        """Liefert ein MySQL-Ziel anhand seines Namens.

        Args:
            name: Zielname (``local`` oder ``uni``).

        Returns:
            Zielkonfiguration als ``MySqlTargetSettings``.

        Raises:
            SettingsError: Wenn ein unbekanntes Ziel angefragt wird.
        """

        normalized = name.lower().strip()
        if normalized == "local":
            return self.local_mysql
        if normalized == "uni":
            return self.uni_mysql
        raise SettingsError(
            f"Unsupported MySQL target '{name}'. Allowed values: local, uni."
        )

    def get_active_mysql_target(self) -> MySqlTargetSettings:
        """Liefert das aktuell konfigurierte aktive MySQL-Ziel."""

        return self.get_mysql_target(self.mysql_active_target)

    def get_fallback_mysql_target(self) -> MySqlTargetSettings | None:
        """Liefert optional das Fallback-Ziel für fehlgeschlagene Target-Checks."""

        if not self.mysql_auto_fallback_to_local:
            return None
        if self.mysql_active_target == "uni":
            return self.local_mysql
        return None


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
    profile_gate_filter_statuses: tuple[str, ...] = ("PASS",)


@dataclass(frozen=True)
class GateConfig:
    """Konfiguration der lokalen Gate-Regeln fuer Profilabrufe."""

    min_trade_value: int = DEFAULT_GATE_MIN_TRADE_VALUE
    require_purchase_event: bool = True
    require_common_stock: bool = True


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
    gate: GateConfig


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
            profile_gate_filter_statuses=_read_csv_status_env(
                "PROFILE_GATE_FILTER_STATUSES", default=("PASS",)
            ),
        ),
        gate=GateConfig(
            min_trade_value=_read_int_env("GATE_MIN_TRADE_VALUE", default=DEFAULT_GATE_MIN_TRADE_VALUE),
            require_purchase_event=_read_bool_env("GATE_REQUIRE_PURCHASE_EVENT", default=True),
            require_common_stock=_read_bool_env("GATE_REQUIRE_COMMON_STOCK", default=True),
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


# Offene Punkte sind zentral dokumentiert in ``docs/todos_offene_fragen.md``.
