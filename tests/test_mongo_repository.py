"""Tests fuer Mongo-Repository-Index und company_key-Bereinigung."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo.errors import DuplicateKeyError

from src.db.mongo_repository import CompanyMongoRepository


class _DeleteResult:
    def __init__(self, deleted_count: int) -> None:
        self.deleted_count = deleted_count


class _UpdateResult:
    def __init__(self, upserted_id: Any = None) -> None:
        self.upserted_id = upserted_id


class _FakeCollection:
    def __init__(self, docs: list[dict[str, Any]] | None = None) -> None:
        self.docs = [dict(doc) for doc in (docs or [])]
        self.indexes: dict[str, dict[str, Any]] = {
            "_id_": {"key": [("_id", 1)], "unique": True}
        }

    def index_information(self) -> dict[str, dict[str, Any]]:
        return dict(self.indexes)

    def drop_index(self, name: str) -> None:
        self.indexes.pop(name, None)

    def create_index(self, keys: list[tuple[str, int]], name: str, unique: bool = False) -> str:
        if unique:
            seen: set[Any] = set()
            field_name = keys[0][0]
            for doc in self.docs:
                key_value = doc.get(field_name)
                if key_value in seen:
                    raise DuplicateKeyError("duplicate key")
                seen.add(key_value)
        self.indexes[name] = {"key": list(keys), "unique": unique}
        return name

    def find(self, _filter: dict[str, Any], projection: dict[str, int]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for doc in self.docs:
            projected: dict[str, Any] = {}
            for field, include in projection.items():
                if include and field in doc:
                    projected[field] = doc[field]
            if "_id" not in projected and "_id" in doc:
                projected["_id"] = doc["_id"]
            result.append(projected)
        return result

    def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        for doc in self.docs:
            company_key_matches = doc.get("company_key") == query.get("company_key")
            if not company_key_matches:
                continue
            threshold = query.get("profile_updated_at", {}).get("$gte")
            profile_updated_at = doc.get("profile_updated_at")
            if threshold is not None and (profile_updated_at is None or profile_updated_at < threshold):
                continue
            return dict(doc)
        return None

    def update_one(self, query: dict[str, Any], update: dict[str, Any], upsert: bool = False) -> _UpdateResult:
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                doc.update(update.get("$set", {}))
                return _UpdateResult()

        if upsert:
            new_doc = dict(query)
            new_doc.update(update.get("$set", {}))
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


class _FakeMongoClientWrapper:
    def __init__(self, collection: _FakeCollection) -> None:
        self._db = {"companies": collection}

    def get_database(self) -> dict[str, _FakeCollection]:
        return self._db


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

