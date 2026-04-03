"""Service zur getrennten Prüfung von MySQL- und MongoDB-Status."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.config.settings import Settings
from src.db.mongo_client import MongoClientWrapper
from src.db.mysql_target_resolver import MySqlResolutionResult, resolve_active_mysql_target


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


class DatabaseStatusService:
    """Ermittelt getrennte Statusinformationen für MySQL und MongoDB."""

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
        except Exception as exc:
            mysql_status = MySqlStatus(
                requested_target=requested_target,
                active_target=None,
                is_connected=False,
                used_fallback=False,
                messages=[f"MySQL-Verbindung fehlgeschlagen: {exc}"],
            )

        try:
            mongo_db = mongo_client.get_database()
            mongo_db.command("ping")
            mongo_status = MongoStatus(is_connected=True, message="MongoDB-Verbindung erfolgreich.")
        except Exception as exc:
            mongo_status = MongoStatus(
                is_connected=False,
                message=f"MongoDB aktuell nicht erreichbar: {exc}",
            )

        return DatabaseStatus(mysql=mysql_status, mongo=mongo_status), mysql_resolution
