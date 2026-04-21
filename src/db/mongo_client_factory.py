"""Factory-Funktionen für MongoDB-Client-Wrapper pro Ziel."""

from __future__ import annotations

from src.config.settings import MongoConfig, MongoSettings
from src.db.mongo_client import MongoClientWrapper


def build_mongo_client_for_target(
    settings: MongoSettings,
    target_name: str,
    *,
    server_selection_timeout_ms: int = 10000,
) -> MongoClientWrapper:
    """Erzeugt einen Mongo-Wrapper für ein konkretes Ziel."""

    target = settings.get_mongo_target(target_name)
    config = MongoConfig(
        active_target=target.name,
        uri=target.uri,
        database=target.database,
        direct_connection=target.direct_connection,
        tls_allow_invalid_certificates=target.tls_allow_invalid_certificates,
    )
    return MongoClientWrapper(config, server_selection_timeout_ms=server_selection_timeout_ms)
