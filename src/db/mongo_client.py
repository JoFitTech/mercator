"""MongoDB-Client-Wrapper für Mercator."""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.database import Database

from src.config.settings import MongoConfig


class MongoClientWrapper:
    """Erzeugt eine MongoDB-Datenbankverbindung für Rohdaten und Profile."""

    def __init__(self, config: MongoConfig, server_selection_timeout_ms: int = 10000) -> None:
        self.config = config
        self._server_selection_timeout_ms = server_selection_timeout_ms
        self._client: MongoClient | None = None

    def get_database(self) -> Database:
        """Liefert die konfigurierte Datenbankinstanz zurück."""
        if self._client is None:
            client_kwargs = {
                "serverSelectionTimeoutMS": self._server_selection_timeout_ms,
            }
            if self.config.direct_connection is not None:
                client_kwargs["directConnection"] = self.config.direct_connection
            if self.config.tls_allow_invalid_certificates:
                client_kwargs["tlsAllowInvalidCertificates"] = True
            self._client = MongoClient(self.config.uri, **client_kwargs)
        return self._client[self.config.database]

    def close(self) -> None:
        """Schließt den internen MongoClient, falls vorhanden."""
        if self._client is not None:
            self._client.close()
            self._client = None
