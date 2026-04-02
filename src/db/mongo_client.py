"""MongoDB-Client für Rohdatenpersistenz."""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.database import Database

from src.config.settings import AppSettings


class MongoDbClient:
    """Erzeugt Mongo-Verbindungen für semistrukturierte Rohdaten."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def get_database(self) -> Database:
        """Liefert die konfigurierte MongoDB-Datenbankinstanz zurück."""
        client = MongoClient(self.settings.mongo_uri)
        return client[self.settings.mongo_database]
