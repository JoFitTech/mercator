"""Resolver-Logik für aktive MySQL-Ziele und optionales Fallback."""

from __future__ import annotations

from src.config.settings import Settings, SettingsError
from src.db.mysql_client import MySqlClient
from src.db.mysql_client_factory import build_mysql_client_for_target


def resolve_active_target(settings: Settings) -> tuple[str, MySqlClient, list[str]]:
    """Löst das aktive MySQL-Ziel robust auf und prüft die Erreichbarkeit.

    Args:
        settings: Geladene MySQL-Gesamtkonfiguration.

    Returns:
        Tupel aus finalem Target-Namen, Client und Hinweisliste.

    Raises:
        SettingsError: Wenn kein nutzbares Ziel aufgelöst werden kann.
    """

    messages: list[str] = []
    active_name = settings.mysql_active_target
    active_client = build_mysql_client_for_target(settings, active_name)

    is_connected, details = active_client.test_connection()
    if is_connected:
        messages.append(details)
        return active_name, active_client, messages

    messages.append(details)
    fallback = settings.get_fallback_mysql_target()
    if fallback is None:
        raise SettingsError(
            f"Active MySQL target '{active_name}' is not reachable and no fallback is configured."
        )

    fallback_client = build_mysql_client_for_target(settings, fallback.name)
    fallback_ok, fallback_details = fallback_client.test_connection()
    messages.append(
        f"Falling back from '{active_name}' to '{fallback.name}' because primary target was unreachable."
    )
    messages.append(fallback_details)

    if not fallback_ok:
        raise SettingsError(
            "Neither active nor fallback MySQL target is reachable. "
            f"Primary: '{active_name}', fallback: '{fallback.name}'."
        )

    return fallback.name, fallback_client, messages
