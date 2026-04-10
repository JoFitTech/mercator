"""Service zur getrennten Prüfung von MySQL- und MongoDB-Status."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.config.settings import Settings
from src.db.mongo_client import MongoClientWrapper
from src.db.mysql_target_resolver import MySqlResolutionResult, resolve_active_mysql_target
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class MySqlStatus:
    """Statusdaten für die aktive MySQL-Auflösung."""

    requested_target: str
    active_target: str | None
    is_connected: bool
    used_fallback: bool
    messages: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MongoStatus:
    """Statusdaten für die MongoDB-Erreichbarkeit."""

    is_connected: bool
    message: str


@dataclass(frozen=True)
class DatabaseStatus:
    """Kombinierter Datenbankstatus für die UI-Ausgabe."""

    mysql: MySqlStatus
    mongo: MongoStatus

    @property
    def is_analysis_available(self) -> bool:
        return self.mysql.is_connected

    @property
    def is_ingestion_available(self) -> bool:
        # Ingestion nutzt Rohdatenspeicherung in Mongo als Pflichtkanal.
        return self.mongo.is_connected

    @property
    def is_any_database_available(self) -> bool:
        return self.mysql.is_connected or self.mongo.is_connected


class DatabaseStatusService:
    """Ermittelt getrennte Statusinformationen für MySQL und MongoDB."""

    def check_mysql_connection(self, mysql_settings: Settings, requested_target: str) -> bool:
        """Prüft die Erreichbarkeit des gewünschten MySQL-Ziels."""

        try:
            resolve_active_mysql_target(settings=mysql_settings, requested_target=requested_target)
            LOGGER.info("db_check mysql connected target=%s", requested_target)
            return True
        except Exception as exc:
            LOGGER.error("db_check mysql failed target=%s error=%s", requested_target, exc)
            return False

    def check_mongo_connection(self, mongo_client: MongoClientWrapper) -> bool:
        """Prüft die Erreichbarkeit von MongoDB."""

        try:
            mongo_client.get_database().command("ping")
            LOGGER.info("db_check mongo connected")
            return True
        except Exception as exc:
            LOGGER.error("db_check mongo failed error=%s", exc)
            return False

    def evaluate(
        self,
        mysql_settings: Settings,
        mongo_client: MongoClientWrapper,
        requested_target: str,
    ) -> tuple[DatabaseStatus, MySqlResolutionResult | None]:
        """Prüft MySQL und MongoDB unabhängig voneinander.

        Args:
            mysql_settings: Geladene MySQL-Konfiguration.
            mongo_client: Wrapper für MongoDB.
            requested_target: Gewünschtes Ziel aus der Laufzeitwahl.

        Returns:
            Tupel aus zusammengefasstem Status und optionalem MySQL-Resolver-Ergebnis.
        """

        mysql_resolution: MySqlResolutionResult | None = None
        LOGGER.info("db_check start requested_mysql_target=%s", requested_target)
        try:
            mysql_resolution = resolve_active_mysql_target(
                settings=mysql_settings,
                requested_target=requested_target,
            )
            mysql_status = MySqlStatus(
                requested_target=mysql_resolution.requested_target,
                active_target=mysql_resolution.active_target,
                is_connected=True,
                used_fallback=mysql_resolution.used_fallback,
                messages=mysql_resolution.messages,
            )
            LOGGER.info(
                "db_check mysql ok requested=%s active=%s fallback=%s",
                mysql_status.requested_target,
                mysql_status.active_target,
                mysql_status.used_fallback,
            )
        except Exception as exc:
            mysql_status = MySqlStatus(
                requested_target=requested_target,
                active_target=None,
                is_connected=False,
                used_fallback=False,
                messages=["MySQL-Verbindung fehlgeschlagen."],
            )
            LOGGER.error("db_check mysql failed requested=%s error=%s", requested_target, exc)

        try:
            mongo_db = mongo_client.get_database()
            mongo_db.command("ping")
            mongo_status = MongoStatus(is_connected=True, message="MongoDB-Verbindung erfolgreich.")
            LOGGER.info("db_check mongo ok")
        except Exception as exc:
            mongo_status = MongoStatus(
                is_connected=False,
                message="MongoDB aktuell nicht erreichbar.",
            )
            LOGGER.error("db_check mongo failed error=%s", exc)

        LOGGER.info(
            "db_check result mysql=%s mongo=%s analysis=%s ingestion=%s",
            mysql_status.is_connected,
            mongo_status.is_connected,
            mysql_status.is_connected,
            mongo_status.is_connected,
        )

        return DatabaseStatus(mysql=mysql_status, mongo=mongo_status), mysql_resolution
