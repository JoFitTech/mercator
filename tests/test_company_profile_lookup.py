from __future__ import annotations

import pandas as pd

from src.services.analysis_service import AnalysisService


class _TradeRepo:
    def fetch_trades(self, filters=None, limit=500):
        return pd.DataFrame([
            {
                "symbol_at_trade": "AAPL",
                "company_key": "SYM:AAPL",
                "acquisition_or_disposition": "A",
                "price": 10,
                "qty": 10,
                "trade_value_estimated": 100,
                "gate_status": "PASS",
                "validation_status": "VALID",
            }
        ])

    def fetch_all_symbols(self):
        return ["AAPL"]


class _CompanyRepo:
    def __init__(self):
        self.row = None

    def fetch_all_symbols(self):
        return []

    def get_company_by_current_symbol(self, symbol):
        return self.row

    def upsert_company(self, payload):
        self.row = payload


class _FmpClient:
    def __init__(self):
        self.calls = 0

    def fetch_company_profile(self, symbol: str):
        self.calls += 1
        return {
            "symbol": symbol,
            "companyName": "Apple Inc.",
            "mktCap": 100,
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "country": "US",
            "exchangeFullName": "NASDAQ",
            "description": "desc",
            "isin": "US0378331005",
            "cik": "0000320193",
            "ceo": "Tim Cook",
            "fullTimeEmployees": "100",
        }


def test_company_lookup_uses_mysql_profile_without_auto_api2_fetch() -> None:
    company_repo = _CompanyRepo()
    company_repo.row = {
        "current_symbol": "AAPL",
        "company_name": "Apple Inc.",
        "description": "desc",
        "profile_status": "FETCHED",
    }
    fmp_client = _FmpClient()
    service = AnalysisService(_TradeRepo(), company_repo, fmp_client=fmp_client)

    result = service.get_ticker_detail("AAPL", accumulate=False)

    assert result.company_profile["symbol"] == "AAPL"
    assert result.company_profile["company_name"] == "Apple Inc."
    assert result.note == "Profildaten verfügbar."
    assert fmp_client.calls == 0


def test_company_lookup_renders_empty_profile_hint_when_mysql_profile_missing() -> None:
    company_repo = _CompanyRepo()
    fmp_client = _FmpClient()
    service = AnalysisService(_TradeRepo(), company_repo, fmp_client=fmp_client)

    result = service.get_ticker_detail("AAPL", accumulate=False)

    assert result.company_profile == {}
    assert "noch nicht geladen" in result.note.lower()
    assert fmp_client.calls == 0
