"""MongoDB-Repositories für Rohtrades und Profile."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import ASCENDING
from pymongo import UpdateOne
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from src.db.mongo_client import MongoClientWrapper

LOGGER = logging.getLogger(__name__)


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

    COMPANY_KEY_INDEX_NAME = "company_key_unique"

    def __init__(self, client: MongoClientWrapper) -> None:
        self.collection: Collection = client.get_database()["companies"]
        self._ensure_company_key_unique_index()

    @staticmethod
    def _normalize_company_key(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _derive_company_key(self, document: dict[str, Any]) -> str | None:
        cik = self._normalize_company_key(document.get("company_cik"))
        if cik:
            return f"CIK:{cik}"
        symbol = self._normalize_company_key(
            document.get("current_symbol") or document.get("symbol")
        )
        if symbol:
            return f"SYM:{symbol.upper()}"
        return None

    def _repair_company_documents(self) -> tuple[int, int, int]:
        """Bereinigt Bestandsdaten fuer konsistente company_key-Werte.

        Returns:
            (derived_keys, removed_invalid_documents, removed_duplicate_documents)
        """

        projections = {
            "_id": 1,
            "company_key": 1,
            "company_cik": 1,
            "current_symbol": 1,
            "symbol": 1,
            "profile_updated_at": 1,
            "updated_at": 1,
        }
        docs = list(self.collection.find({}, projections))
        if not docs:
            return 0, 0, 0

        derived_keys = 0
        invalid_ids: list[Any] = []
        groups: dict[str, list[dict[str, Any]]] = {}

        for doc in docs:
            normalized_key = self._normalize_company_key(doc.get("company_key"))
            if not normalized_key:
                normalized_key = self._derive_company_key(doc)
                if normalized_key:
                    self.collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"company_key": normalized_key}},
                    )
                    doc["company_key"] = normalized_key
                    derived_keys += 1

            if not normalized_key:
                invalid_ids.append(doc["_id"])
                continue

            doc["company_key"] = normalized_key
            groups.setdefault(normalized_key, []).append(doc)

        removed_invalid = 0
        if invalid_ids:
            removed_invalid = self.collection.delete_many({"_id": {"$in": invalid_ids}}).deleted_count

        removed_duplicates = 0
        for company_key, same_key_docs in groups.items():
            if len(same_key_docs) <= 1:
                continue

            same_key_docs.sort(
                key=lambda item: (
                    item.get("profile_updated_at") or datetime.min.replace(tzinfo=timezone.utc),
                    item.get("updated_at") or datetime.min.replace(tzinfo=timezone.utc),
                    str(item.get("_id")),
                ),
                reverse=True,
            )
            duplicate_ids = [doc["_id"] for doc in same_key_docs[1:]]
            if duplicate_ids:
                removed_duplicates += self.collection.delete_many({"_id": {"$in": duplicate_ids}}).deleted_count
                LOGGER.warning(
                    "Mongo companies cleanup removed %s duplicate docs for company_key=%s.",
                    len(duplicate_ids),
                    company_key,
                )

        return derived_keys, removed_invalid, removed_duplicates

    def _ensure_company_key_unique_index(self) -> None:
        index_info = self.collection.index_information()
        for index_name, definition in index_info.items():
            keys = definition.get("key")
            is_company_key_index = isinstance(keys, list) and keys == [("company_key", ASCENDING)]
            if not is_company_key_index:
                continue

            is_strict_unique = (
                bool(definition.get("unique"))
                and not bool(definition.get("sparse"))
                and not definition.get("partialFilterExpression")
            )
            if is_strict_unique:
                return

            self.collection.drop_index(index_name)

        derived, removed_invalid, removed_duplicates = self._repair_company_documents()
        if derived or removed_invalid or removed_duplicates:
            LOGGER.warning(
                "Mongo companies cleanup applied: derived_keys=%s removed_invalid=%s removed_duplicates=%s",
                derived,
                removed_invalid,
                removed_duplicates,
            )

        try:
            self.collection.create_index(
                [("company_key", ASCENDING)],
                name=self.COMPANY_KEY_INDEX_NAME,
                unique=True,
            )
        except DuplicateKeyError as exc:
            raise RuntimeError(
                "Mongo companies index build failed after cleanup. "
                "Please inspect collection 'companies' for duplicate/invalid company_key values."
            ) from exc

    def get_recent_profile(self, company_key: str, ttl_days: int) -> dict[str, Any] | None:
        """Lädt ein Profil, sofern es jünger als TTL-Tage ist."""
        normalized_key = self._normalize_company_key(company_key)
        if not normalized_key:
            return None
        threshold = datetime.now(timezone.utc) - timedelta(days=ttl_days)
        return self.collection.find_one(
            {"company_key": normalized_key, "profile_updated_at": {"$gte": threshold}}
        )

    def get_profile(self, company_key: str) -> dict[str, Any] | None:
        """Lädt ein Profil unabhängig von TTL anhand des company_key."""

        normalized_key = self._normalize_company_key(company_key)
        if not normalized_key:
            return None
        return self.collection.find_one({"company_key": normalized_key})

    def upsert_profile(self, company: dict[str, Any]) -> None:
        """Speichert oder aktualisiert ein Profil nach `company_key`."""
        normalized_key = self._normalize_company_key(company.get("company_key"))
        if not normalized_key:
            raise ValueError(
                "CompanyMongoRepository.upsert_profile requires a non-empty 'company_key'."
            )
        payload = {k: v for k, v in dict(company).items() if v is not None}
        payload["company_key"] = normalized_key
        existing = self.collection.find_one(
            {"company_key": normalized_key},
            {"profile_status": 1, "profile_reason": 1},
        )
        # Ein bereits angereichertes Profil darf nicht durch einen Stub zurückgestuft werden.
        if (
            existing
            and str(existing.get("profile_status") or "").upper() == "FETCHED"
            and str(payload.get("profile_status") or "").upper() == "NOT_REQUESTED"
        ):
            payload.pop("profile_status", None)
            payload.pop("profile_reason", None)

        try:
            self.collection.update_one(
                {"company_key": normalized_key},
                {"$set": payload},
                upsert=True,
            )
        except DuplicateKeyError:
            # Race Condition: In der Zeit zwischen find_one und update_one wurde der Key angelegt.
            # Ein zweiter Versuch als reines Update ist sicher.
            self.collection.update_one(
                {"company_key": normalized_key},
                {"$set": payload},
                upsert=False,
            )

    def upsert_profiles(self, companies: list[dict[str, Any]], batch_size: int = 200) -> int:
        if not companies:
            return 0
        written = 0
        for start in range(0, len(companies), batch_size):
            chunk = companies[start : start + batch_size]
            ops: list[UpdateOne] = []
            for company in chunk:
                normalized_key = self._normalize_company_key(company.get("company_key"))
                if not normalized_key:
                    continue
                payload = {k: v for k, v in dict(company).items() if v is not None}
                payload["company_key"] = normalized_key
                ops.append(
                    UpdateOne(
                        {"company_key": normalized_key},
                        {"$set": payload},
                        upsert=True,
                    )
                )
            if not ops:
                continue
            self.collection.bulk_write(ops, ordered=False)
            written += len(ops)
        return written

    def count_all(self) -> int:
        """Liefert Anzahl der gespeicherten Profile."""
        return self.collection.count_documents({})


class AppSettingsMongoRepository:
    """Persistiert App-Einstellungen in MongoDB."""

    SETTINGS_ID = "runtime_gate_settings"

    def __init__(self, client: MongoClientWrapper) -> None:
        self.collection: Collection = client.get_database()["app_settings"]

    def load(self) -> dict[str, Any] | None:
        return self.collection.find_one({"_id": self.SETTINGS_ID})

    def save(self, payload: dict[str, Any]) -> None:
        self.collection.update_one(
            {"_id": self.SETTINGS_ID},
            {"$set": payload},
            upsert=True,
        )

    def reset(self) -> None:
        self.collection.delete_one({"_id": self.SETTINGS_ID})
