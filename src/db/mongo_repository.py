"""MongoDB-Repositories für Rohtrades und Profile."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo.collection import Collection

from src.db.mongo_client import MongoClientWrapper


class InsiderTradeMongoRepository:
    """Verwaltet Rohdaten in `insider_trades_raw` inklusive Deduplizierungsschlüssel."""

    def __init__(self, client: MongoClientWrapper) -> None:
        self.collection: Collection = client.get_database()["insider_trades_raw"]
        self.collection.create_index("dedupe_key", unique=True)

    def upsert_raw_trades(self, trades: list[dict[str, Any]]) -> int:
        """Schreibt Rohtrades als Upsert in MongoDB.

        Args:
            trades: Liste normalisierter Trade-Dicts.

        Returns:
            int: Anzahl erfolgreich verarbeiteter Upserts.
        """

        count = 0
        for trade in trades:
            result = self.collection.update_one(
                {"dedupe_key": trade["dedupe_key"]},
                {"$setOnInsert": trade},
                upsert=True,
            )
            if result.upserted_id is not None:
                count += 1
        return count

    def count_all(self) -> int:
        """Liefert die Anzahl aller Rohdatensätze."""
        return self.collection.count_documents({})


class CompanyMongoRepository:
    """Verwaltet Unternehmensprofile in der Collection `companies` mit TTL-Logik."""

    def __init__(self, client: MongoClientWrapper) -> None:
        self.collection: Collection = client.get_database()["companies"]
        self.collection.create_index("symbol", unique=True)

    def get_recent_profile(self, symbol: str, ttl_days: int) -> dict[str, Any] | None:
        """Lädt ein Profil, sofern es jünger als TTL-Tage ist."""
        threshold = datetime.now(timezone.utc) - timedelta(days=ttl_days)
        return self.collection.find_one(
            {"symbol": symbol.upper(), "profile_updated_at": {"$gte": threshold}}
        )

    def upsert_profile(self, company: dict[str, Any]) -> None:
        """Speichert oder aktualisiert ein Profil nach Symbol."""
        self.collection.update_one(
            {"symbol": company["symbol"]},
            {"$set": company},
            upsert=True,
        )

    def count_all(self) -> int:
        """Liefert Anzahl der gespeicherten Profile."""
        return self.collection.count_documents({})
