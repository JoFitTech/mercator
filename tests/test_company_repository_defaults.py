from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from src.db.repositories.company_repository import CompanyRepository, CompanyMySqlRepository
from src.services.import_service import ImportService


class _DummyClient:
    def __init__(self) -> None:
        self.last_sql = None
        self.last_params = None

    def execute(self, sql, params):
        self.last_sql = sql
        self.last_params = params
        return 1


def test_company_repository_defaults_sector_resolution_status_when_missing() -> None:
    dummy_client = _DummyClient()
    repo = CompanyRepository(cast(Any, dummy_client))
    repo.upsert_company({"company_key": "SYM:AAPL", "current_symbol": "AAPL"})

    assert dummy_client.last_params is not None
    assert dummy_client.last_params["sector_resolution_status"] == "UNRESOLVED"


def test_company_repository_defaults_sector_resolution_status_when_none() -> None:
    dummy_client = _DummyClient()
    repo = CompanyRepository(cast(Any, dummy_client))
    repo.upsert_company(
        {
            "company_key": "SYM:AAPL",
            "current_symbol": "AAPL",
            "sector_resolution_status": None,
        }
    )

    assert dummy_client.last_params is not None
    assert dummy_client.last_params["sector_resolution_status"] == "UNRESOLVED"


def test_import_service_stub_sets_unresolved_sector_status() -> None:
    class _MongoRepo:
        def __init__(self) -> None:
            self.last_payload = None

        def upsert_profile(self, payload):
            self.last_payload = payload

    class _CompanyRepo:
        def __init__(self) -> None:
            self.last_payload = None

        def upsert_company(self, payload):
            self.last_payload = payload

    mongo_repo = _MongoRepo()
    company_repo = _CompanyRepo()

    service = ImportService(
        fmp_client=cast(Any, object()),
        gate_evaluator=cast(Any, object()),
        raw_repo=cast(Any, object()),
        company_mongo_repo=cast(Any, mongo_repo),
        trade_mysql_repo=None,
        company_mysql_repo=cast(Any, company_repo),
    )

    fetched_at = datetime.now(timezone.utc)
    service._upsert_company_stub(
        {
            "company_key": "SYM:MSFT",
            "company_cik": "0000789019",
            "symbol": "MSFT",
        },
        fetched_at,
    )

    assert mongo_repo.last_payload is not None
    assert company_repo.last_payload is not None
    assert mongo_repo.last_payload["sector_resolution_status"] == "UNRESOLVED"
    assert company_repo.last_payload["sector_resolution_status"] == "UNRESOLVED"


class _CursorStub:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = rows
        self.description = [("current_symbol",)]
        self.executed_sql: str | None = None
        self.executed_params: tuple[Any, ...] | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.executed_sql = str(sql)
        self.executed_params = tuple(params)

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class _ConnectionStub:
    def __init__(self, cursor: _CursorStub) -> None:
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor


class _ClientForBackfill:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.cursor_stub = _CursorStub(rows)

    def get_connection(self):
        return _ConnectionStub(self.cursor_stub)


def test_backfill_candidates_query_is_mysql_strict_mode_compatible() -> None:
    client = _ClientForBackfill(rows=[("msft",), ("aapl",)])
    repo = CompanyMySqlRepository(cast(Any, client))

    symbols = repo.list_profile_backfill_candidates(limit=50)

    assert symbols == ["MSFT", "AAPL"]
    assert client.cursor_stub.executed_sql is not None
    assert "SELECT DISTINCT" not in client.cursor_stub.executed_sql
    assert "GROUP BY c.current_symbol" in client.cursor_stub.executed_sql
    assert "ORDER BY MAX(COALESCE(c.last_seen_at, c.updated_at)) DESC" in client.cursor_stub.executed_sql
    assert client.cursor_stub.executed_params == (50,)


def test_company_repository_resolves_symbol_by_current_symbol_or_company_key() -> None:
    row = ("SYM:AAPL", "AAPL", "Apple Inc.", "FETCHED")
    client = _ClientForBackfill(rows=[row])
    client.cursor_stub.description = [("company_key",), ("current_symbol",), ("company_name",), ("profile_status",)]
    repo = CompanyMySqlRepository(cast(Any, client))

    result = repo.resolve_symbol(" aapl ")

    assert result == {
        "company_key": "SYM:AAPL",
        "current_symbol": "AAPL",
        "company_name": "Apple Inc.",
        "profile_status": "FETCHED",
    }
    assert client.cursor_stub.executed_params == ("AAPL", "SYM:AAPL", "AAPL")
    assert "UPPER(current_symbol)" in str(client.cursor_stub.executed_sql)


def test_company_repository_reads_stock_profile_status_fields() -> None:
    updated_at = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    row = ("SYM:MSFT", "MSFT", "Microsoft", "FETCHED", "stock_import", updated_at, "FMP", "RESOLVED")
    client = _ClientForBackfill(rows=[row])
    client.cursor_stub.description = [
        ("company_key",),
        ("current_symbol",),
        ("company_name",),
        ("profile_status",),
        ("profile_reason",),
        ("profile_updated_at",),
        ("profile_provider",),
        ("sector_resolution_status",),
    ]
    repo = CompanyMySqlRepository(cast(Any, client))

    result = repo.get_stock_profile_status("msft")

    assert result is not None
    assert result["company_key"] == "SYM:MSFT"
    assert result["profile_status"] == "FETCHED"
    assert result["profile_updated_at"] == updated_at
    assert "profile_updated_at" in str(client.cursor_stub.executed_sql)
