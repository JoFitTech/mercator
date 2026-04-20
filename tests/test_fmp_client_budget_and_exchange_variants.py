from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from src.config.settings import FmpConfig
from src.data_sources.fmp_client import FmpApiError, FmpClient


class _UsageStub:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed
        self.calls = 0

    def can_make_call(self, provider: str = "fmp", limit: int = 250) -> bool:
        return self.allowed

    def track_call(self, provider: str = "fmp", limit: int = 250) -> None:
        self.calls += 1


def _client(usage: _UsageStub) -> FmpClient:
    return FmpClient(config=FmpConfig(base_url="https://example.com", api_key="real_key"), api_usage_service=usage)


def test_budget_exhausted_degrades_gracefully() -> None:
    usage = _UsageStub(allowed=False)
    with pytest.raises(FmpApiError):
        _client(usage).fetch_exchange_variants("AAPL")


@patch("src.data_sources.fmp_client.requests.get")
def test_fetch_exchange_variants_maps_list_response(mock_get: Mock) -> None:
    response = Mock()
    response.status_code = 200
    response.json.return_value = [{"symbol": "AAPL", "exchange": "NASDAQ"}]
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    usage = _UsageStub(allowed=True)
    result = _client(usage).fetch_exchange_variants("AAPL")
    assert result[0]["exchange"] == "NASDAQ"
    assert usage.calls == 1
