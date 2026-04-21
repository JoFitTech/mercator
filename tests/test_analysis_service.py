"""Smoke-Test für AnalysisService mit Fake-Repositories."""

import pandas as pd

from src.services.analysis_service import AnalysisService


class _FakeTradeRepo:
    def fetch_trades(self, filters=None, limit=500):
        # Wir geben acquisition_or_disposition mit, damit direction gemappt werden kann
        return pd.DataFrame(
            [
                {"symbol": "AAPL", "symbol_at_trade": "AAPL", "price": 10.0, "qty": 2.0, "acquisition_or_disposition": "A", "gate_status": "PASS"},
                {"symbol": "AAPL", "symbol_at_trade": "AAPL", "price": 20.0, "qty": 3.0, "acquisition_or_disposition": "D", "gate_status": "PASS"},
            ]
        )


class _FakeCompanyRepo:
    def fetch_company(self, company_key: str):
        return pd.DataFrame([{"company_key": company_key, "company_name": "Apple Inc."}])

    def get_company_by_current_symbol(self, symbol: str):
        return {"current_symbol": symbol, "company_name": "Apple Inc."}

    def upsert_company(self, payload):
        return None

    def fetch_all_symbols(self):
        return ["AAPL"]


class _MinimalTradeRepo:
    def fetch_trades(self, filters=None, limit=500):
        return pd.DataFrame(
            [
                {
                    "company_key": "AAPL",
                    "symbol_at_trade": "AAPL",
                    "acquisition_or_disposition": "A",
                    "securities_transacted": "5",
                    "price": "10.5",
                }
            ]
        )


def test_analysis_service_ticker_detail_smoke() -> None:
    """Der Service soll Kennzahlen ohne DB-Verbindung berechnen."""
    service = AnalysisService(_FakeTradeRepo(), _FakeCompanyRepo())
    result = service.get_ticker_detail("AAPL", accumulate=False)
    assert result.metrics["trade_count"] == 2
    assert result.metrics["avg_price"] == 15.0
    assert result.company_profile["company_name"] == "Apple Inc."
    # Richtung muss gemappt sein
    assert result.rows[0]["direction"] == "BUY"
    assert result.rows[1]["direction"] == "SELL"


def test_analysis_service_direction_mapping() -> None:
    """Prüft ob direction auch bei get_filtered_trades vorhanden ist."""
    service = AnalysisService(_FakeTradeRepo(), _FakeCompanyRepo())
    df = service.get_filtered_trades(accumulate=False)
    assert "direction" in df.columns
    assert df.iloc[0]["direction"] == "BUY"


def test_analysis_service_ensures_missing_ui_columns() -> None:
    service = AnalysisService(_MinimalTradeRepo(), _FakeCompanyRepo())
    df = service.get_filtered_trades(accumulate=False)

    assert "direction" in df.columns
    assert "score" in df.columns
    assert "score_class" in df.columns
    assert "qty" in df.columns
    assert "trade_value_estimated" in df.columns
    assert df.iloc[0]["direction"] == "BUY"


def test_get_filtered_trades_no_keyerror_with_missing_score_columns() -> None:
    service = AnalysisService(_MinimalTradeRepo(), _FakeCompanyRepo())
    df = service.get_filtered_trades(accumulate=True)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "score" in df.columns
    assert "score_class" in df.columns
    assert df.iloc[0]["symbol_at_trade"] == "AAPL"


class _InvalidDateTradeRepo:
    def fetch_trades(self, filters=None, limit=500):
        return pd.DataFrame(
            [
                {
                    "company_key": "AAPL",
                    "symbol_at_trade": "AAPL",
                    "acquisition_or_disposition": "A",
                    "transaction_date": "not-a-date",
                    "qty": 5,
                    "price": 10.5,
                    "trade_value_estimated": 52.5,
                }
            ]
        )


def test_get_filtered_trades_falls_back_when_transaction_date_is_unparseable() -> None:
    service = AnalysisService(_InvalidDateTradeRepo(), _FakeCompanyRepo())
    df = service.get_filtered_trades(accumulate=True)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["symbol_at_trade"] == "AAPL"
    assert df.iloc[0]["direction"] == "BUY"


def test_get_ticker_detail_stable_with_reduced_data() -> None:
    service = AnalysisService(_MinimalTradeRepo(), _FakeCompanyRepo())
    result = service.get_ticker_detail("AAPL", accumulate=True)

    assert result.metrics["trade_count"] == 1
    assert isinstance(result.rows, list)
    assert len(result.rows) == 1
    assert "score" in result.rows[0]
    assert "score_class" in result.rows[0]


class _PagedTradeRepo:
    def __init__(self) -> None:
        self.count_filters = None
        self.page_filters = None
        self.page_offset = None

    def count_trades(self, filters=None):
        self.count_filters = dict(filters or {})
        return 3

    def fetch_trades_page(self, filters=None, limit=100, offset=0):
        self.page_filters = dict(filters or {})
        self.page_offset = offset
        return pd.DataFrame(
            [
                {
                    "symbol_at_trade": "AAPL",
                    "acquisition_or_disposition": "A",
                    "qty": 1,
                    "price": 500000,
                    "trade_value_estimated": 500000,
                    "trade_republic_universe_status": "IN_UNIVERSE",
                }
            ]
        )


def test_get_filtered_trades_page_uses_same_filter_basis_and_clamps_offset() -> None:
    repo = _PagedTradeRepo()
    service = AnalysisService(repo, _FakeCompanyRepo())  # type: ignore[arg-type]

    df, total = service.get_filtered_trades_page(
        filters={"symbol": "AAPL", "trade_republic_universe_status": "IN_UNIVERSE"},
        limit=2,
        offset=10,
        min_value=400000,
    )

    assert total == 3
    assert repo.count_filters == repo.page_filters
    assert repo.count_filters["min_value"] == 400000
    assert repo.page_offset == 2
    assert len(df) == 1
