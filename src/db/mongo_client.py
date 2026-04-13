"""MongoDB-Client-Wrapper für Mercator."""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.database import Database

from src.config.settings import MongoConfig


class MongoClientWrapper:
    """Erzeugt eine MongoDB-Datenbankverbindung für Rohdaten und Profile."""

    def __init__(self, config: MongoConfig, server_selection_timeout_ms: int = 3000) -> None:
        self.config = config
        self._server_selection_timeout_ms = server_selection_timeout_ms
        self._client: MongoClient | None = None

    def get_database(self) -> Database:
        """Liefert die konfigurierte Datenbankinstanz zurück."""
        if self._client is None:
            self._client = MongoClient(
                self.config.uri,
                serverSelectionTimeoutMS=self._server_selection_timeout_ms,
            )
        return self._client[self.config.database]

    def close(self) -> None:
        """Schließt den internen MongoClient, falls vorhanden."""
        if self._client is not None:
            self._client.close()
            self._client = None
