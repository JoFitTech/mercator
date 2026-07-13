"""Tests fuer Mongo-Repository-Index und company_key-Bereinigung."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import UpdateOne
from pymongo.errors import DuplicateKeyError

from src.db.mongo_repository import CompanyMongoRepository, RawProviderResponseMongoRepository
from src.models.stock import RawProviderResponse


class _DeleteResult:
    def __init__(self, deleted_count: int) -> None:
        self.deleted_count = deleted_count


class _UpdateResult:
    def __init__(self, upserted_id: Any = None) -> None:
        self.upserted_id = upserted_id


class _FakeCollection:
    def __init__(self, docs: list[dict[str, Any]] | None = None) -> None:
        self.docs = [dict(doc) for doc in (docs or [])]
        self.dropped_indexes: list[str] = []
        self._next_generated_id = 1000
        self.indexes: dict[str, dict[str, Any]] = {
            "_id_": {"key": [("_id", 1)], "unique": True}
        }

    @staticmethod
    def _extract_index_key(doc: dict[str, Any], fields: list[tuple[str, int]]) -> tuple[Any, ...]:
        return tuple(doc.get(field_name) for field_name, _ in fields)

    def _ensure_unique_constraints(self, candidate: dict[str, Any], *, skip_doc: dict[str, Any] | None = None) -> None:
        for definition in self.indexes.values():
            if not definition.get("unique"):
                continue
            keys = definition.get("key")
            if not isinstance(keys, list):
                continue
            candidate_key = self._extract_index_key(candidate, keys)
            for existing in self.docs:
                if skip_doc is not None and existing is skip_doc:
                    continue
                if self._extract_index_key(existing, keys) == candidate_key:
                    raise DuplicateKeyError("duplicate key")

    def index_information(self) -> dict[str, dict[str, Any]]:
        return dict(self.indexes)

    def drop_index(self, name: str) -> None:
        self.dropped_indexes.append(name)
        self.indexes.pop(name, None)

    def create_index(self, keys: list[tuple[str, int]], name: str, unique: bool = False) -> str:
        if unique:
            seen: set[tuple[Any, ...]] = set()
            for doc in self.docs:
                key_value = self._extract_index_key(doc, keys)
                if key_value in seen:
                    raise DuplicateKeyError("duplicate key")
                seen.add(key_value)
        self.indexes[name] = {"key": list(keys), "unique": unique}
        return name

    @staticmethod
    def _matches_filter(doc: dict[str, Any], query: dict[str, Any]) -> bool:
        for key, expected in query.items():
            if isinstance(expected, dict) and "$in" in expected:
                if doc.get(key) not in expected["$in"]:
                    return False
                continue
            if isinstance(expected, dict) and "$gte" in expected:
                value = doc.get(key)
                if value is None or value < expected["$gte"]:
                    return False
                continue
            if doc.get(key) != expected:
                return False
        return True

    def find(self, query: dict[str, Any], projection: dict[str, int] | None = None) -> "_FakeCursor":
        result: list[dict[str, Any]] = []
        for doc in self.docs:
            if not self._matches_filter(doc, query):
                continue
            if projection is None:
                result.append(dict(doc))
                continue
            if projection and all(include == 0 for include in projection.values()):
                projected = {
                    field: value
                    for field, value in doc.items()
                    if projection.get(field, 1) != 0
                }
            else:
                projected = {}
                for field, include in projection.items():
                    if include and field in doc:
                        projected[field] = doc[field]
                if "_id" not in projected and "_id" in doc:
                    projected["_id"] = doc["_id"]
            result.append(projected)
        return _FakeCursor(result)

    def find_one(self, query: dict[str, Any], projection: dict[str, int] | None = None) -> dict[str, Any] | None:
        for doc in self.docs:
            company_key_matches = doc.get("company_key") == query.get("company_key")
            if not company_key_matches:
                continue
            threshold = query.get("profile_updated_at", {}).get("$gte")
            profile_updated_at = doc.get("profile_updated_at")
            if threshold is not None and (profile_updated_at is None or profile_updated_at < threshold):
                continue
            if projection is None:
                return dict(doc)
            projected: dict[str, Any] = {}
            for field, include in projection.items():
                if include and field in doc:
                    projected[field] = doc[field]
            if "_id" in doc:
                projected.setdefault("_id", doc["_id"])
            return projected
        return None

    def update_one(self, query: dict[str, Any], update: dict[str, Any], upsert: bool = False) -> _UpdateResult:
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                candidate = dict(doc)
                candidate.update(update.get("$set", {}))
                self._ensure_unique_constraints(candidate, skip_doc=doc)
                doc.update(candidate)
                return _UpdateResult()

        if upsert:
            new_doc = dict(query)
            new_doc.update(update.get("$set", {}))
            if new_doc.get("_id") is None:
                new_doc["_id"] = self._next_generated_id
                self._next_generated_id += 1
            self._ensure_unique_constraints(new_doc)
            self.docs.append(new_doc)
            return _UpdateResult(upserted_id=new_doc.get("_id", True))

        return _UpdateResult()

    def delete_many(self, query: dict[str, Any]) -> _DeleteResult:
        ids = set(query.get("_id", {}).get("$in", []))
        before = len(self.docs)
        self.docs = [doc for doc in self.docs if doc.get("_id") not in ids]
        return _DeleteResult(before - len(self.docs))

    def count_documents(self, _query: dict[str, Any]) -> int:
        return len(self.docs)

    def aggregate(self, _pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for doc in self.docs:
            category = doc.get("category")
            if category is None:
                continue
            counts[str(category)] = counts.get(str(category), 0) + 1
        return [{"_id": category, "count": count} for category, count in counts.items()]

    def bulk_write(self, operations: list[UpdateOne], ordered: bool = False) -> None:
        for op in operations:
            query = getattr(op, "_filter")
            update = getattr(op, "_doc")
            upsert = bool(getattr(op, "_upsert"))
            self.update_one(query, update, upsert=upsert)


class _FakeMongoClientWrapper:
    def __init__(self, collection: _FakeCollection, raw_collection: _FakeCollection | None = None) -> None:
        self._db = {"companies": collection}
        if raw_collection is not None:
            self._db["raw_provider_responses"] = raw_collection

    def get_database(self) -> dict[str, _FakeCollection]:
        return self._db


class _FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self.docs = docs

    def sort(self, field_name: str, direction: int) -> "_FakeCursor":
        reverse = direction < 0
        self.docs.sort(key=lambda doc: doc.get(field_name) or datetime.min.replace(tzinfo=timezone.utc), reverse=reverse)
        return self

    def limit(self, value: int) -> "_FakeCursor":
        self.docs = self.docs[:value]
        return self

    def __iter__(self):
        return iter(self.docs)


def test_raw_provider_response_repository_upserts_and_sanitizes_request_params() -> None:
    raw_collection = _FakeCollection([])
    repo = RawProviderResponseMongoRepository(_FakeMongoClientWrapper(_FakeCollection([]), raw_collection))
    fetched_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    response_id = repo.upsert_response(
        RawProviderResponse(
            provider="fmp",
            category="company_profile",
            request_hash="hash-1",
            status="FAILED",
            fetched_at=fetched_at,
            symbol="AAPL",
            request_params={"symbol": "AAPL", "apikey": "secret", "nested": {"token": "hidden"}},
            payload={"raw": "payload"},
            error_message="rate limited",
        )
    )

    assert response_id == "hash-1"
    assert raw_collection.docs[0]["status"] == "FAILED"
    assert raw_collection.docs[0]["request_params"] == {"symbol": "AAPL", "nested": {}}
    assert raw_collection.docs[0]["payload"] == {"raw": "payload"}


def test_raw_provider_response_repository_lists_latest_by_symbol_and_category() -> None:
    older = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    newer = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    raw_collection = _FakeCollection(
        [
            {"request_hash": "old", "symbol": "AAPL", "category": "company_profile", "fetched_at": older},
            {"request_hash": "new", "symbol": "AAPL", "category": "company_profile", "fetched_at": newer},
            {"request_hash": "price", "symbol": "AAPL", "category": "historical_price", "fetched_at": newer},
            {"request_hash": "other", "symbol": "MSFT", "category": "company_profile", "fetched_at": newer},
        ]
    )
    repo = RawProviderResponseMongoRepository(_FakeMongoClientWrapper(_FakeCollection([]), raw_collection))

    docs = repo.list_responses("AAPL", category="company_profile", limit=1)

    assert [doc["request_hash"] for doc in docs] == ["new"]
    assert "_id" not in docs[0]


def test_raw_provider_response_repository_counts_by_category() -> None:
    raw_collection = _FakeCollection(
        [
            {"request_hash": "1", "category": "company_profile"},
            {"request_hash": "2", "category": "company_profile"},
            {"request_hash": "3", "category": "historical_price"},
        ]
    )
    repo = RawProviderResponseMongoRepository(_FakeMongoClientWrapper(_FakeCollection([]), raw_collection))

    assert repo.count_by_category() == {"company_profile": 2, "historical_price": 1}


def test_company_repository_requires_non_empty_company_key() -> None:
    collection = _FakeCollection([])
    repo = CompanyMongoRepository(_FakeMongoClientWrapper(collection))

    try:
        repo.upsert_profile({"company_key": "   "})
    except ValueError as exc:
        assert "non-empty 'company_key'" in str(exc)
    else:
        assert False, "upsert_profile() should reject empty company_key"


def test_company_repository_repairs_documents_before_unique_index() -> None:
    now = datetime.now(timezone.utc)
    docs = [
        {"_id": 1, "company_key": None, "company_cik": "0001", "updated_at": now},
        {"_id": 2, "company_key": "", "updated_at": now},
        {"_id": 3, "company_key": "SYM:ABC", "updated_at": datetime(2024, 1, 1, tzinfo=timezone.utc)},
        {"_id": 4, "company_key": "SYM:ABC", "updated_at": datetime(2025, 1, 1, tzinfo=timezone.utc)},
    ]
    collection = _FakeCollection(docs)

    CompanyMongoRepository(_FakeMongoClientWrapper(collection))

    by_id = {doc["_id"]: doc for doc in collection.docs}
    assert 2 not in by_id
    assert 3 not in by_id
    assert by_id[1]["company_key"] == "CIK:0001"
    assert by_id[4]["company_key"] == "SYM:ABC"

    index_definition = collection.index_information()["company_key_unique"]
    assert index_definition["unique"] is True
    assert index_definition["key"] == [("company_key", 1)]


def test_company_repository_keeps_valid_company_key_index_without_unneeded_drops() -> None:
    collection = _FakeCollection([])
    collection.indexes["company_key_unique"] = {
        "key": [("company_key", 1)],
        "unique": True,
    }

    CompanyMongoRepository(_FakeMongoClientWrapper(collection))

    assert collection.index_information()["company_key_unique"]["unique"] is True
    assert collection.dropped_indexes == []


def test_company_repository_removes_legacy_symbol_index_and_rebuilds_company_key_index() -> None:
    docs = [
        {"_id": 1, "company_key": "SYM:AAA", "symbol": None},
        {"_id": 2, "company_key": "SYM:BBB", "symbol": None},
    ]
    collection = _FakeCollection(docs)
    collection.indexes["symbol_1"] = {
        "key": [("symbol", 1)],
        "unique": True,
    }

    CompanyMongoRepository(_FakeMongoClientWrapper(collection))

    assert "symbol_1" not in collection.index_information()
    assert "symbol_1" in collection.dropped_indexes
    assert collection.index_information()["company_key_unique"]["unique"] is True


def test_company_repository_derives_company_key_from_current_symbol() -> None:
    docs = [{"_id": 1, "company_key": None, "current_symbol": " msft "}]
    collection = _FakeCollection(docs)

    CompanyMongoRepository(_FakeMongoClientWrapper(collection))

    assert collection.docs[0]["company_key"] == "SYM:MSFT"


def test_company_repository_removes_docs_without_derivable_company_key() -> None:
    docs = [
        {"_id": 1, "company_key": None, "company_name": "No key"},
        {"_id": 2, "company_key": "SYM:OK", "current_symbol": "OK"},
    ]
    collection = _FakeCollection(docs)

    CompanyMongoRepository(_FakeMongoClientWrapper(collection))

    remaining_ids = {doc["_id"] for doc in collection.docs}
    assert remaining_ids == {2}


def test_upsert_profiles_with_current_symbol_only_payload_is_not_blocked_by_legacy_symbol_index() -> None:
    docs = [{"_id": 1, "company_key": "SYM:LEGACY", "symbol": None}]
    collection = _FakeCollection(docs)
    collection.indexes["symbol_1"] = {
        "key": [("symbol", 1)],
        "unique": True,
    }

    repo = CompanyMongoRepository(_FakeMongoClientWrapper(collection))
    written = repo.upsert_profiles(
        [
            {"company_key": "SYM:AAPL", "current_symbol": "AAPL"},
            {"company_key": "SYM:MSFT", "current_symbol": "MSFT"},
        ]
    )

    assert written == 2
    assert "symbol_1" not in collection.index_information()
    assert {doc["company_key"] for doc in collection.docs} >= {"SYM:AAPL", "SYM:MSFT"}


def test_upsert_profile_does_not_downgrade_fetched_status_with_stub() -> None:
    now = datetime.now(timezone.utc)
    docs = [
        {
            "_id": 1,
            "company_key": "SYM:ABC",
            "profile_status": "FETCHED",
            "profile_reason": "api_fetch",
            "company_name": "ABC Corp",
            "updated_at": now,
        }
    ]
    collection = _FakeCollection(docs)
    repo = CompanyMongoRepository(_FakeMongoClientWrapper(collection))

    repo.upsert_profile(
        {
            "company_key": "SYM:ABC",
            "profile_status": "NOT_REQUESTED",
            "profile_reason": None,
            "last_seen_at": now,
        }
    )

    updated = next(doc for doc in collection.docs if doc["company_key"] == "SYM:ABC")
    assert updated["profile_status"] == "FETCHED"
    assert updated["profile_reason"] == "api_fetch"
    assert updated["company_name"] == "ABC Corp"


def test_raw_provider_response_repository_keeps_partial_failed_and_rate_limited_payloads() -> None:
    raw_collection = _FakeCollection([])
    repo = RawProviderResponseMongoRepository(_FakeMongoClientWrapper(_FakeCollection([]), raw_collection))
    fetched_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    for status in ["PARTIAL_SUCCESS", "FAILED", "RATE_LIMITED"]:
        repo.upsert_response(
            RawProviderResponse(
                provider="fmp",
                category="historical_price",
                request_hash=f"hash-{status}",
                status=status,
                fetched_at=fetched_at,
                symbol="AAPL",
                request_params={"symbol": "AAPL"},
                payload={"status": status},
                error_message="provider returned partial/error state" if status != "PARTIAL_SUCCESS" else None,
            )
        )

    statuses = {doc["status"] for doc in raw_collection.docs}
    assert statuses == {"PARTIAL_SUCCESS", "FAILED", "RATE_LIMITED"}
    assert all(doc["payload"]["status"] == doc["status"] for doc in raw_collection.docs)
