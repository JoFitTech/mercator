"""Resolver-Logik für aktive Mongo-Ziele und optionales Fallback."""

from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import MongoSettings, SettingsError
from src.db.mongo_client import MongoClientWrapper
from src.db.mongo_client_factory import build_mongo_client_for_target


@dataclass(frozen=True)
class MongoResolutionResult:
    """Ergebnisstruktur der Mongo-Target-Auflösung."""

    requested_target: str
    active_target: str
    client: MongoClientWrapper
    used_fallback: bool
    messages: list[str]


def _probe_mongo_wrapper(wrapper: MongoClientWrapper) -> tuple[bool, str, Exception | None]:
    try:
        wrapper.get_database().command("ping")
        return True, f"Mongo target '{wrapper.config.active_target}' reachable.", None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc), exc


def resolve_active_mongo_target(
    settings: MongoSettings, requested_target: str | None = None
) -> MongoResolutionResult:
    """Löst das aktive Mongo-Ziel robust auf und prüft die Erreichbarkeit."""

    messages: list[str] = []
    active_name = (requested_target or settings.mongo_active_target).strip().lower()
    active_client = build_mongo_client_for_target(settings, active_name)

    is_connected, details, active_exc = _probe_mongo_wrapper(active_client)
    if is_connected:
        messages.append(details)
        return MongoResolutionResult(
            requested_target=active_name,
            active_target=active_name,
            client=active_client,
            used_fallback=False,
            messages=messages,
        )

    messages.append(details)
    fallback = settings.get_fallback_mongo_target()
    if fallback is None:
        raise SettingsError(
            f"Active Mongo target '{active_name}' is not reachable and no fallback is configured. "
            f"Details: {details}"
        ) from active_exc

    fallback_client = build_mongo_client_for_target(settings, fallback.name)
    fallback_ok, fallback_details, fallback_exc = _probe_mongo_wrapper(fallback_client)
    messages.append(
        f"Falling back from '{active_name}' to '{fallback.name}' because primary target was unreachable."
    )
    messages.append(fallback_details)

    if not fallback_ok:
        raise SettingsError(
            "Neither active nor fallback Mongo target is reachable. "
            f"Primary: '{active_name}', fallback: '{fallback.name}'. "
            f"Primary details: {details} | Fallback details: {fallback_details}"
        ) from fallback_exc

    return MongoResolutionResult(
        requested_target=active_name,
        active_target=fallback.name,
        client=fallback_client,
        used_fallback=True,
        messages=messages,
    )
