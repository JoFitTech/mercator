"""MongoDB-Client-Wrapper für FinanzPort Academic."""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.database import Database

from src.config.settings import MongoConfig


class MongoClientWrapper:
    """Erzeugt eine MongoDB-Datenbankverbindung für Rohdaten und Profile."""

    def __init__(self, config: MongoConfig) -> None:
        self.config = config

    def get_database(self) -> Database:
        """Liefert die konfigurierte Datenbankinstanz zurück."""
        client = MongoClient(self.config.uri, serverSelectionTimeoutMS=3000)
        return client[self.config.database]
