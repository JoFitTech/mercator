from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.db.repositories.fundamental_metrics_repository import FundamentalMetricsRepository
from src.db.repositories.stock_price_repository import StockPriceRepository


def _build_mysql_mock() -> tuple[MagicMock, MagicMock, MagicMock]:
    client = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    client.get_connection.return_value.__enter__.return_value = conn
    client.get_connection.return_value.__exit__.return_value = False
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.cursor.return_value.__exit__.return_value = False
    return client, conn, cursor


def test_stock_price_repository_upserts_lists_and_reads_latest_date() -> None:
    client, conn, cursor = _build_mysql_mock()
    repo = StockPriceRepository(client)
    refreshed_at = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)

    written = repo.upsert_prices([
        {
            "symbol": "aapl",
            "price_date": date(2026, 7, 8),
            "open_price": 200,
            "high_price": 205,
            "low_price": 198,
            "close_price": 204,
            "adjusted_close": 204,
            "volume": 123456,
            "provider": "fmp",
            "source_refreshed_at": refreshed_at,
            "quality_status": "ready",
        }
    ])

    assert written == 1
    sql, params = cursor.executemany.call_args[0]
    assert "INSERT INTO stock_price_history" in sql
    assert params[0]["symbol"] == "AAPL"
    assert params[0]["provider"] == "FMP"
    assert params[0]["quality_status"] == "READY"
    conn.commit.assert_called()

    cursor.description = [("symbol",), ("price_date",), ("close_price",)]
    cursor.fetchall.return_value = [("AAPL", date(2026, 7, 8), 204)]
    rows = repo.list_prices("aapl", provider="fmp", limit=10)
    assert rows == [{"symbol": "AAPL", "price_date": date(2026, 7, 8), "close_price": 204}]

    cursor.fetchone.return_value = (date(2026, 7, 8),)
    assert repo.get_latest_price_date("aapl") == date(2026, 7, 8)


def test_stock_price_repository_requires_symbol_and_price_date() -> None:
    repo = StockPriceRepository(_build_mysql_mock()[0])
    with pytest.raises(ValueError):
        repo.upsert_prices([{"symbol": "", "price_date": date(2026, 1, 1)}])
    with pytest.raises(ValueError):
        repo.upsert_prices([{"symbol": "AAPL"}])


def test_fundamental_metrics_repository_upserts_and_lists_metrics() -> None:
    client, conn, cursor = _build_mysql_mock()
    repo = FundamentalMetricsRepository(client)

    written = repo.upsert_metrics([
        {
            "symbol": "msft",
            "metric_name": "revenue_growth",
            "period_type": "annual",
            "period_end": date(2025, 12, 31),
            "value": 0.13,
            "unit": "ratio",
            "provider": "fmp",
            "quality_status": "ready",
        }
    ])

    assert written == 1
    sql, params = cursor.executemany.call_args[0]
    assert "INSERT INTO fundamental_metrics" in sql
    assert params[0]["symbol"] == "MSFT"
    assert params[0]["period_type"] == "ANNUAL"
    assert params[0]["provider"] == "FMP"
    conn.commit.assert_called()

    cursor.description = [("symbol",), ("metric_name",), ("value",)]
    cursor.fetchall.return_value = [("MSFT", "revenue_growth", 0.13)]
    rows = repo.list_metrics("msft", metric_name="revenue_growth", provider="fmp")
    assert rows == [{"symbol": "MSFT", "metric_name": "revenue_growth", "value": 0.13}]


def test_fundamental_metrics_repository_requires_identity_fields() -> None:
    repo = FundamentalMetricsRepository(_build_mysql_mock()[0])
    with pytest.raises(ValueError):
        repo.upsert_metrics([{"symbol": "AAPL", "period_end": date(2025, 12, 31)}])
    with pytest.raises(ValueError):
        repo.upsert_metrics([{"symbol": "AAPL", "metric_name": "market_cap"}])
