"""Resolver-Logik für aktive MySQL-Ziele und optionales Fallback."""

from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import Settings, SettingsError
from src.db.mysql_client import MySqlClient
from src.db.mysql_client_factory import build_mysql_client_for_target


@dataclass(frozen=True)
class MySqlResolutionResult:
    """Ergebnisstruktur der MySQL-Target-Auflösung."""

    requested_target: str
    active_target: str
    client: MySqlClient
    used_fallback: bool
    messages: list[str]


def resolve_active_mysql_target(
    settings: Settings, requested_target: str | None = None
) -> MySqlResolutionResult:
    """Löst das aktive MySQL-Ziel robust auf und prüft die Erreichbarkeit.

    Args:
        settings: Geladene MySQL-Gesamtkonfiguration.
        requested_target: Optionales Ziel aus der Laufzeitwahl.

    Returns:
        Aufgelöstes Ziel inklusive Status-Hinweisen.

    Raises:
        SettingsError: Wenn kein nutzbares Ziel aufgelöst werden kann.
    """

    messages: list[str] = []
    active_name = (requested_target or settings.mysql_active_target).strip().lower()
    active_client = build_mysql_client_for_target(settings, active_name)

    is_connected, details = active_client.test_connection()
    if is_connected:
        messages.append(details)
        return MySqlResolutionResult(
            requested_target=active_name,
            active_target=active_name,
            client=active_client,
            used_fallback=False,
            messages=messages,
        )

    messages.append(details)
    fallback = settings.get_fallback_mysql_target()
    if fallback is None:
        raise SettingsError(
            f"Active MySQL target '{active_name}' is not reachable and no fallback is configured. "
            f"Details: {details}"
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
            f"Primary: '{active_name}', fallback: '{fallback.name}'. "
            f"Primary details: {details} | Fallback details: {fallback_details}"
        )

    return MySqlResolutionResult(
        requested_target=active_name,
        active_target=fallback.name,
        client=fallback_client,
        used_fallback=True,
        messages=messages,
    )


def resolve_active_target(settings: Settings) -> tuple[str, MySqlClient, list[str]]:
    """Kompatibilitätswrapper für bestehende Aufrufer im Projekt."""

    resolved = resolve_active_mysql_target(settings=settings, requested_target=None)
    return resolved.active_target, resolved.client, resolved.messages
