"""Tests fuer MySQL-Repositories ohne echte DB-Verbindung."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any, cast

from src.db.mysql_repository import CompanyRepository


class _DummyCursor:
    def __init__(self) -> None:
        self.sql: str | None = None
        self.params: dict | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql: str, params: dict) -> None:
        self.sql = sql
        self.params = params


class _DummyConnection:
    def __init__(self) -> None:
        self.cursor_instance = _DummyCursor()
        self.committed = False

    def cursor(self) -> _DummyCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True


class _DummyClient:
    def __init__(self) -> None:
        self.conn = _DummyConnection()

    @contextmanager
    def connection(self):
        yield self.conn


def test_upsert_company_ignores_non_sql_fields() -> None:
    """Zusaetzliche Felder (z. B. dict-Payload) duerfen MySQL-Params nicht brechen."""

    client = _DummyClient()
    repo = CompanyRepository(cast(Any, client))
    company = {
        "symbol": "AAPL",
        "company_name": "Apple Inc.",
        "market_cap": 1,
        "price": 1.0,
        "currency": "USD",
        "cik": "0000320193",
        "isin": "US0378331005",
        "cusip": "037833100",
        "exchange": "NASDAQ",
        "exchange_full_name": "NASDAQ Global Select",
        "industry": "Consumer Electronics",
        "sector": "Technology",
        "country": "US",
        "website": "https://apple.com",
        "description": "Test",
        "ceo": "Tim Cook",
        "full_time_employees": "161000",
        "ipo_date": "1980-12-12",
        "is_etf": False,
        "is_actively_trading": True,
        "is_adr": False,
        "is_fund": False,
        "profile_updated_at": datetime(2026, 4, 3),
        "profile_payload": {"raw": "value"},
    }

    repo.upsert_company(company)

    assert client.conn.committed is True
    assert client.conn.cursor_instance.params is not None
    assert "profile_payload" not in client.conn.cursor_instance.params
    assert client.conn.cursor_instance.params["symbol"] == "AAPL"

