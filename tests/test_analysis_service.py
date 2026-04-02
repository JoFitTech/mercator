"""Smoke-Test für AnalysisService mit Fake-Repositories."""

import pandas as pd

from src.services.analysis_service import AnalysisService


class _FakeTradeRepo:
    def fetch_trades(self, filters=None, limit=500):
        return pd.DataFrame(
            [
                {"symbol": "AAPL", "price": 10.0, "qty": 2.0},
                {"symbol": "AAPL", "price": 20.0, "qty": 3.0},
            ]
        )


class _FakeCompanyRepo:
    def fetch_company(self, symbol: str):
        return pd.DataFrame([{"symbol": symbol, "company_name": "Apple Inc."}])


def test_analysis_service_ticker_detail_smoke() -> None:
    """Der Service soll Kennzahlen ohne DB-Verbindung berechnen."""
    service = AnalysisService(_FakeTradeRepo(), _FakeCompanyRepo())
    result = service.get_ticker_detail("AAPL")
    assert result.metrics["trade_count"] == 2
    assert result.metrics["avg_price"] == 15.0
    assert result.company_profile["company_name"] == "Apple Inc."
