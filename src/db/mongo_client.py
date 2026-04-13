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

    def get_database(self) -> Database:
        """Liefert die konfigurierte Datenbankinstanz zurück."""
        client = MongoClient(
            self.config.uri,
            serverSelectionTimeoutMS=self._server_selection_timeout_ms,
        )
        return client[self.config.database]
