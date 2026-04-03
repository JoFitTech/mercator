"""Factory-Funktionen zum Erzeugen von MySQL-Clients pro Ziel."""

from __future__ import annotations

from src.config.settings import Settings
from src.db.mysql_client import MySqlClient


def build_mysql_client_for_target(settings: Settings, target_name: str) -> MySqlClient:
    """Erzeugt einen MySQL-Client für das gewünschte Ziel.

    Args:
        settings: Geladene MySQL-Gesamtkonfiguration.
        target_name: Zielname (``local`` oder ``uni``).

    Returns:
        Einen konfigurierten ``MySqlClient``.
    """

    return MySqlClient(settings.get_mysql_target(target_name))


def build_active_mysql_client(settings: Settings) -> MySqlClient:
    """Erzeugt einen MySQL-Client für das aktuell aktive Ziel.

    Args:
        settings: Geladene MySQL-Gesamtkonfiguration.

    Returns:
        Einen konfigurierten ``MySqlClient``.
    """

    return MySqlClient(settings.get_active_mysql_target())
