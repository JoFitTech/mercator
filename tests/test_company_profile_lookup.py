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
    def fetch_company_profile(self, symbol: str):
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


def test_company_lookup_uses_symbol_and_fallback_to_api2() -> None:
    company_repo = _CompanyRepo()
    service = AnalysisService(_TradeRepo(), company_repo, fmp_client=_FmpClient())

    result = service.get_ticker_detail("AAPL", accumulate=False)

    assert result.company_profile["symbol"] == "AAPL"
    assert result.company_profile["company_name"] == "Apple Inc."
    assert result.note == "Profildaten verfügbar."


def test_company_lookup_renders_empty_profile_hint_when_api2_unavailable() -> None:
    company_repo = _CompanyRepo()
    service = AnalysisService(_TradeRepo(), company_repo, fmp_client=None)

    result = service.get_ticker_detail("AAPL", accumulate=False)

    assert result.company_profile == {}
    assert "nicht verfügbar" in result.note.lower()
