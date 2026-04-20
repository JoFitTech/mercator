"""MongoDB-Zielauflöser mit Fallback-Logik (analog MySQL-Resolver)."""

from __future__ import annotations

from dataclasses import dataclass

from pymongo import MongoClient

from src.config.settings import MongoConfig
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class MongoResolutionResult:
    """Ergebnis der Mongo-Zielauflösung."""

    requested_target: str
    active_target: str | None
    used_fallback: bool
    uri: str | None
    database: str | None
    messages: list[str]


def resolve_active_mongo_target(
    mongo_config: MongoConfig,
    requested_target: str,
    fallback_enabled: bool = True,
    server_selection_timeout_ms: int = 5000,
) -> MongoResolutionResult:
    """Löst das aktive MongoDB-Ziel mit optionalem Fallback auf.

    Falls das angeforderte Ziel nicht erreichbar ist und `fallback_enabled=True`,
    wird automatisch auf das lokale Ziel zurückgegriffen.

    Args:
        mongo_config: MongoDB-Konfiguration mit targets.
        requested_target: Gewünschtes Ziel (z.B. "uni" oder "local").
        fallback_enabled: Bei True wird auf "local" zurückgegriffen, wenn das Ziel fehlt.
        server_selection_timeout_ms: Timeout für Connection-Versuche.

    Returns:
        MongoResolutionResult mit aktuellem Target, URI, Database und Status.

    Raises:
        RuntimeError: Falls kein erreichbares Target gefunden wurde.
    """

    messages: list[str] = []

    # Primäres Ziel auflösen
    if requested_target == "uni":
        uri = mongo_config.uni_uri
        database = mongo_config.uni_database
        target_name = "uni"
    elif requested_target == "local":
        uri = mongo_config.local_uri
        database = mongo_config.local_database
        target_name = "local"
    else:
        raise RuntimeError(f"Unbekanntes MongoDB-Target: {requested_target}")

    # Prüfe, ob das primäre Ziel erreichbar ist
    if uri and _test_mongo_connection(uri, timeout_ms=server_selection_timeout_ms):
        messages.append(f"MongoDB-Ziel '{target_name}' ist erreichbar.")
        LOGGER.info("mongo_resolve target=%s uri=%s ok", target_name, uri)
        return MongoResolutionResult(
            requested_target=requested_target,
            active_target=target_name,
            used_fallback=False,
            uri=uri,
            database=database,
            messages=messages,
        )

    # Fallback, falls primäres Ziel nicht erreichbar
    if not fallback_enabled:
        messages.append(f"MongoDB-Ziel '{target_name}' ist nicht erreichbar und Fallback ist deaktiviert.")
        LOGGER.error("mongo_resolve target=%s not reachable and fallback disabled", target_name)
        raise RuntimeError(f"MongoDB-Ziel '{target_name}' nicht erreichbar und Fallback deaktiviert.")

    # Versuche Fallback auf "local"
    if requested_target != "local":
        fallback_uri = mongo_config.local_uri
        fallback_database = mongo_config.local_database
        if fallback_uri and _test_mongo_connection(fallback_uri, timeout_ms=server_selection_timeout_ms):
            messages.append(
                f"MongoDB-Ziel '{target_name}' nicht erreichbar. Fallback auf 'local' erfolgreich."
            )
            LOGGER.warning("mongo_resolve fallback from %s to local", target_name)
            return MongoResolutionResult(
                requested_target=requested_target,
                active_target="local",
                used_fallback=True,
                uri=fallback_uri,
                database=fallback_database,
                messages=messages,
            )

    # Kein Fallback möglich
    messages.append(f"MongoDB-Ziel '{target_name}' nicht erreichbar und kein Fallback verfügbar.")
    LOGGER.error("mongo_resolve no target reachable")
    raise RuntimeError("Kein erreichbares MongoDB-Ziel gefunden.")


def _test_mongo_connection(uri: str, timeout_ms: int = 5000) -> bool:
    """Prüft, ob eine MongoDB-Verbindung erreichbar ist."""
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms, connectTimeoutMS=timeout_ms)
        client.admin.command("ping")
        client.close()
        return True
    except Exception as exc:
        LOGGER.debug("mongo_test_connection failed uri=%s error=%s", uri, exc)
        return False

