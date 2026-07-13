from __future__ import annotations

from typing import Any

from src.config.settings import FmpConfig
from src.data_sources.fmp_client import FmpClient


class _FmpClientSpy(FmpClient):
    def __init__(self, payload: Any) -> None:
        super().__init__(FmpConfig(base_url="https://example.test", api_key="real-test-key"))
        self.payload = payload
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _request(self, endpoint: str, params: dict[str, Any], retries: int = 2) -> Any:  # noqa: ARG002
        self.calls.append((endpoint, params))
        return self.payload


def test_fmp_client_fetches_stock_profile_and_historical_prices() -> None:
    profile_client = _FmpClientSpy([{"symbol": "AAPL", "companyName": "Apple Inc."}])
    assert profile_client.fetch_company_profile("AAPL") == {"symbol": "AAPL", "companyName": "Apple Inc."}
    assert profile_client.calls[0][0] == "/profile"
    assert profile_client.calls[0][1]["symbol"] == "AAPL"

    price_client = _FmpClientSpy([{"date": "2026-01-02", "close": 200}])
    assert price_client.fetch_historical_price_eod_full("AAPL", "2026-01-01", "2026-01-31") == [
        {"date": "2026-01-02", "close": 200}
    ]
    assert price_client.calls[0][0] == "/historical-price-eod/full"
    assert price_client.calls[0][1]["from"] == "2026-01-01"
    assert price_client.calls[0][1]["to"] == "2026-01-31"


def test_fmp_client_fetches_financial_and_valuation_endpoints() -> None:
    client = _FmpClientSpy([{"date": "2025-12-31", "revenue": 100}])

    assert client.fetch_income_statement("msft", period="quarter", limit=4) == client.payload
    assert client.fetch_balance_sheet_statement("msft") == client.payload
    assert client.fetch_key_metrics("msft") == client.payload
    assert client.fetch_ratios("msft") == client.payload

    endpoints = [endpoint for endpoint, _params in client.calls]
    assert endpoints == ["/income-statement", "/balance-sheet-statement", "/key-metrics", "/ratios"]
    assert client.calls[0][1]["period"] == "quarter"
    assert client.calls[0][1]["limit"] == 4
    assert all(params["symbol"] == "msft" for _endpoint, params in client.calls)
