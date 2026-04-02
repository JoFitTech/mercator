"""Repository-Schicht für Rohdaten in MongoDB."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.db.mongo_client import MongoDbClient


class MongoRepository:
    """Kapselt Zugriff auf Rohdaten-Collections in MongoDB."""

    def __init__(self, client: MongoDbClient) -> None:
        self.client = client

    def save_raw_trades(self, raw_df: pd.DataFrame, collection_name: str = "raw_trades") -> int:
        """Speichert Rohdaten in MongoDB.

        Returns:
            int: Anzahl zu speichernder Dokumente (Platzhalterwert).
        """
        # TODO: insert_many mit robustem Fehlerhandling ergänzen.
        return len(raw_df.index)

    def fetch_raw_trades(self, collection_name: str = "raw_trades") -> list[dict[str, Any]]:
        """Liest Rohdaten aus MongoDB als Dokumentliste."""
        # TODO: Reale Mongo-Abfrage ergänzen.
        return []
