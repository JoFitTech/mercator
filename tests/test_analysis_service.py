"""Smoke-Test für AnalysisService mit Fake-Repositories."""

import pandas as pd

from src.services.analysis_service import AnalysisService


class _FakeTradeRepo:
    def fetch_trades(self, filters=None, limit=500):
        # Wir geben acquisition_or_disposition mit, damit direction gemappt werden kann
        return pd.DataFrame(
            [
                {"symbol": "AAPL", "symbol_at_trade": "AAPL", "price": 10.0, "qty": 2.0, "acquisition_or_disposition": "A"},
                {"symbol": "AAPL", "symbol_at_trade": "AAPL", "price": 20.0, "qty": 3.0, "acquisition_or_disposition": "D"},
            ]
        )


class _FakeCompanyRepo:
    def fetch_company(self, company_key: str):
        return pd.DataFrame([{"company_key": company_key, "company_name": "Apple Inc."}])


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
    assert "score" in df.columns
    assert "score_class" in df.columns


def test_get_ticker_detail_stable_with_reduced_data() -> None:
    service = AnalysisService(_MinimalTradeRepo(), _FakeCompanyRepo())
    result = service.get_ticker_detail("AAPL", accumulate=True)

    assert result.metrics["trade_count"] == 1
    assert isinstance(result.rows, list)
    assert len(result.rows) == 1
    assert "score" in result.rows[0]
    assert "score_class" in result.rows[0]

