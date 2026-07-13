from __future__ import annotations

from datetime import date, datetime, timezone

from src.preprocessing.normalization import (
    normalize_company_profile_payload,
    normalize_fundamental_metric_payload,
    normalize_historical_price_payload,
)


def test_normalize_company_profile_payload_maps_fmp_profile_to_company_row() -> None:
    fetched_at = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)

    row = normalize_company_profile_payload(
        {
            "symbol": "aapl",
            "companyName": "Apple Inc.",
            "marketCap": "3000000000000",
            "price": "210.5",
            "sector": "Technology",
            "ipoDate": "1980-12-12",
            "isEtf": False,
        },
        symbol="aapl",
        fetched_at=fetched_at,
    )

    assert row["company_key"] == "SYM:AAPL"
    assert row["current_symbol"] == "AAPL"
    assert row["company_name"] == "Apple Inc."
    assert row["market_cap"] == 3_000_000_000_000
    assert row["price"] == 210.5
    assert row["ipo_date"] == date(1980, 12, 12)
    assert row["profile_status"] == "FETCHED"
    assert row["profile_updated_at"] == fetched_at


def test_normalize_historical_price_payload_skips_rows_without_date() -> None:
    fetched_at = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)

    rows = normalize_historical_price_payload(
        [
            {"date": "2026-07-08", "open": "200", "high": "205", "low": "198", "close": "204", "adjClose": "204", "volume": "123456"},
            {"date": "", "close": "999"},
        ],
        symbol="aapl",
        fetched_at=fetched_at,
    )

    assert len(rows) == 1
    assert rows[0]["symbol"] == "AAPL"
    assert rows[0]["price_date"] == date(2026, 7, 8)
    assert rows[0]["close_price"] == 204.0
    assert rows[0]["volume"] == 123456
    assert rows[0]["quality_status"] == "READY"


def test_normalize_fundamental_metric_payload_extracts_selected_metrics() -> None:
    rows = normalize_fundamental_metric_payload(
        [{"date": "2025-12-31", "revenueGrowth": "0.12", "grossProfitMargin": "0.45", "unused": "1"}],
        symbol="msft",
        metric_fields={"revenueGrowth": "revenue_growth", "grossProfitMargin": "gross_margin"},
        period_type="annual",
        unit="ratio",
    )

    assert rows == [
        {
            "symbol": "MSFT",
            "metric_name": "revenue_growth",
            "period_type": "annual",
            "period_end": date(2025, 12, 31),
            "value": 0.12,
            "unit": "ratio",
            "provider": "FMP",
            "source_refreshed_at": None,
            "quality_status": "READY",
        },
        {
            "symbol": "MSFT",
            "metric_name": "gross_margin",
            "period_type": "annual",
            "period_end": date(2025, 12, 31),
            "value": 0.45,
            "unit": "ratio",
            "provider": "FMP",
            "source_refreshed_at": None,
            "quality_status": "READY",
        },
    ]
