from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from src.services.feature_engineering_service import FeatureEngineeringService
from src.services.historical_market_data_service import HistoricalMarketDataService


class _PriceRepo:
    def __init__(self, rows):
        self.rows = rows

    def list_prices(self, symbol: str, limit: int = 500):
        return self.rows


class _MetricsRepo:
    def __init__(self, rows):
        self.rows = rows

    def list_metrics(self, symbol: str, limit: int = 500):
        return self.rows


class _FeatureRepo:
    def __init__(self) -> None:
        self.saved = []

    def upsert_feature(self, feature) -> None:
        self.saved.append(feature)


class _WatchlistRepo:
    def list_items(self, active_only: bool = True):
        return [{"symbol": "aapl"}, {"symbol": "msft"}]


class _DataQualityRepo:
    def __init__(self) -> None:
        self.issues = []

    def create_issue(self, issue):
        self.issues.append(issue)
        return len(self.issues)


def _price_rows(count: int, start: date = date(2025, 1, 1)):
    refreshed_at = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    return [
        {
            "symbol": "AAPL",
            "price_date": start + timedelta(days=index),
            "close_price": 100 + index,
            "adjusted_close": 100 + index,
            "volume": 1_000_000 + (index * 1000),
            "source_refreshed_at": refreshed_at,
        }
        for index in range(count)
    ]


def _complete_metrics():
    period = date(2025, 12, 31)
    refreshed_at = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    return [
        {"symbol": "AAPL", "metric_name": "revenue_growth", "period_end": period, "value": 0.12, "source_refreshed_at": refreshed_at},
        {"symbol": "AAPL", "metric_name": "gross_margin", "period_end": period, "value": 0.44, "source_refreshed_at": refreshed_at},
        {"symbol": "AAPL", "metric_name": "pe_ratio", "period_end": period, "value": 25.5, "source_refreshed_at": refreshed_at},
        {"symbol": "AAPL", "metric_name": "debt_to_equity", "period_end": period, "value": 1.2, "source_refreshed_at": refreshed_at},
        {"symbol": "AAPL", "metric_name": "market_cap", "period_end": period, "value": 3_000_000_000, "source_refreshed_at": refreshed_at},
    ]


def _service(price_rows, metric_rows, watchlist_repo=None):
    technical_repo = _FeatureRepo()
    fundamental_repo = _FeatureRepo()
    dq_repo = _DataQualityRepo()
    service = FeatureEngineeringService(
        price_repository=_PriceRepo(price_rows),
        metrics_repository=_MetricsRepo(metric_rows),
        technical_feature_repository=technical_repo,
        fundamental_feature_repository=fundamental_repo,
        watchlist_repository=watchlist_repo,
        data_quality_repository=dq_repo,
    )
    return service, technical_repo, fundamental_repo, dq_repo


def test_price_feature_helper_calculates_ready_technical_features() -> None:
    payload = HistoricalMarketDataService.calculate_price_features(_price_rows(220))

    assert payload["feature_status"] == "READY"
    assert payload["feature_date"] == date(2025, 8, 8)
    assert round(payload["sma_20"], 4) == 309.5
    assert round(payload["sma_50"], 4) == 294.5
    assert round(payload["sma_200"], 4) == 219.5
    assert payload["momentum_1m"] is not None
    assert payload["momentum_3m"] is not None
    assert payload["momentum_6m"] is not None
    assert payload["volume_trend_20d"] is not None


def test_feature_engineering_service_persists_ready_features_without_quality_issue() -> None:
    service, technical_repo, fundamental_repo, dq_repo = _service(_price_rows(220), _complete_metrics())

    summary = service.calculate_for_symbol("aapl")

    assert summary.symbol == "AAPL"
    assert summary.status == "READY"
    assert summary.technical.feature_status == "READY"
    assert summary.fundamental.feature_status == "READY"
    assert summary.fundamental.valuation_ratio == 25.5
    assert technical_repo.saved[0].symbol == "AAPL"
    assert fundamental_repo.saved[0].market_cap == 3_000_000_000
    assert dq_repo.issues == []


def test_feature_engineering_service_records_quality_issues_for_short_history_and_missing_metrics() -> None:
    service, _, _, dq_repo = _service(_price_rows(40), [])

    summary = service.calculate_for_symbol("msft")

    assert summary.status == "MISSING"
    assert summary.technical.feature_status == "INCOMPLETE"
    assert summary.fundamental.feature_status == "MISSING"
    assert [issue.data_category for issue in dq_repo.issues] == ["technical_features", "fundamental_features"]


def test_feature_engineering_service_calculates_all_watchlist_symbols() -> None:
    service, technical_repo, _, _ = _service(_price_rows(220), _complete_metrics(), watchlist_repo=_WatchlistRepo())

    summaries = service.calculate_for_watchlist()

    assert [summary.symbol for summary in summaries] == ["AAPL", "MSFT"]
    assert len(technical_repo.saved) == 2
