from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.db.repositories.feature_repository import FundamentalFeatureRepository, TechnicalFeatureRepository
from src.models.features import FundamentalFeatures, TechnicalFeatures


def _build_mysql_mock() -> tuple[MagicMock, MagicMock, MagicMock]:
    client = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    client.get_connection.return_value.__enter__.return_value = conn
    client.get_connection.return_value.__exit__.return_value = False
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.cursor.return_value.__exit__.return_value = False
    return client, conn, cursor


def test_technical_feature_repository_upserts_and_reads_latest() -> None:
    client, conn, cursor = _build_mysql_mock()
    repo = TechnicalFeatureRepository(client)
    refreshed_at = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)

    repo.upsert_feature(
        TechnicalFeatures(
            symbol="aapl",
            feature_date=date(2026, 7, 8),
            sma_20=200.5,
            feature_status="ready",
            unavailable_reason="",
            input_refreshed_at=refreshed_at,
        )
    )

    sql, params = cursor.execute.call_args[0]
    assert "INSERT INTO technical_features" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert params["symbol"] == "AAPL"
    assert params["feature_status"] == "READY"
    assert params["unavailable_reason"] == ""
    assert params["input_refreshed_at"] == refreshed_at
    conn.commit.assert_called()

    cursor.description = [("symbol",), ("feature_date",), ("sma_20",)]
    cursor.fetchone.return_value = ("AAPL", date(2026, 7, 8), 200.5)
    assert repo.get_latest("aapl") == {"symbol": "AAPL", "feature_date": date(2026, 7, 8), "sma_20": 200.5}


def test_fundamental_feature_repository_upserts_and_lists() -> None:
    client, conn, cursor = _build_mysql_mock()
    repo = FundamentalFeatureRepository(client)

    repo.upsert_feature(
        FundamentalFeatures(
            symbol="msft",
            feature_period=date(2025, 12, 31),
            revenue_growth=0.12,
            market_cap=3_000_000_000,
            feature_status="incomplete",
            unavailable_reason="Missing valuation_ratio.",
        )
    )

    sql, params = cursor.execute.call_args[0]
    assert "INSERT INTO fundamental_features" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert params["symbol"] == "MSFT"
    assert params["feature_status"] == "INCOMPLETE"
    assert params["unavailable_reason"] == "Missing valuation_ratio."
    conn.commit.assert_called()

    cursor.description = [("symbol",), ("feature_period",), ("market_cap",)]
    cursor.fetchall.return_value = [("MSFT", date(2025, 12, 31), 3_000_000_000)]
    assert repo.list_features("msft") == [
        {"symbol": "MSFT", "feature_period": date(2025, 12, 31), "market_cap": 3_000_000_000}
    ]


def test_feature_repositories_require_identity_fields() -> None:
    tech_repo = TechnicalFeatureRepository(_build_mysql_mock()[0])
    fundamental_repo = FundamentalFeatureRepository(_build_mysql_mock()[0])

    with pytest.raises(ValueError):
        tech_repo.upsert_feature({"symbol": "", "feature_date": date(2026, 1, 1)})
    with pytest.raises(ValueError):
        tech_repo.upsert_feature({"symbol": "AAPL"})
    with pytest.raises(ValueError):
        fundamental_repo.upsert_feature({"symbol": "", "feature_period": date(2025, 12, 31)})
    with pytest.raises(ValueError):
        fundamental_repo.upsert_feature({"symbol": "AAPL"})
