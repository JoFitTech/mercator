from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

import pandas as pd

from src.services.analysis_service import AnalysisService
from src.services.trade_republic_universe_service import (
    TR_STATUS_IN,
    TR_STATUS_NOT_IN,
    TR_STATUS_UNKNOWN,
    TradeRepublicUniverseIngestionService,
    TradeRepublicUniverseMatchingService,
)


class _StubCursor:
    def __init__(self, scripted):
        self._scripted = scripted
        self._index = 0

    def execute(self, *_args, **_kwargs):
        return None

    def fetchone(self):
        if self._index >= len(self._scripted):
            return None
        row = self._scripted[self._index]
        self._index += 1
        if isinstance(row, list):
            return None
        return row

    def fetchall(self):
        if self._index >= len(self._scripted):
            return []
        row = self._scripted[self._index]
        self._index += 1
        return row if isinstance(row, list) else []

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return None


class _StubConn:
    def __init__(self, scripted):
        self._scripted = scripted

    def cursor(self, **_kwargs):
        return _StubCursor(self._scripted)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return None


class _StubClient:
    def __init__(self, scripted):
        self._scripted = scripted

    @contextmanager
    def connection(self):
        yield _StubConn(self._scripted)


def test_parse_universe_csv_filters_invalid_rows() -> None:
    payload = "isin,symbol,instrument_name,country,type\nDE000BASF111,BASF,BASF SE,DE,Stock\n,,Broken,DE,Stock\n"
    parsed = TradeRepublicUniverseIngestionService.parse_universe_csv(payload)
    assert len(parsed) == 1
    assert parsed[0].isin == "DE000BASF111"


def test_parse_universe_csv_empty_source() -> None:
    assert TradeRepublicUniverseIngestionService.parse_universe_csv("") == []


def test_matching_exact_isin_match() -> None:
    service = TradeRepublicUniverseMatchingService(
        _StubClient(
            [
                {"source_last_refreshed_at": datetime(2026, 1, 1, 0, 0, 0)},
                {"isin": "DE000BASF111", "instrument_name": "BASF SE"},
            ]
        )
    )
    result = service.match_company("DE000BASF111", "BAS", "BASF SE")
    assert result.status == TR_STATUS_IN
    assert result.match_method == "ISIN"


def test_matching_not_in_universe_after_refresh() -> None:
    service = TradeRepublicUniverseMatchingService(
        _StubClient(
            [
                {"source_last_refreshed_at": datetime(2026, 1, 1, 0, 0, 0)},
                None,
            ]
        )
    )
    result = service.match_company("US0000000001", "ZZZ", "Unknown Co")
    assert result.status == TR_STATUS_NOT_IN


def test_matching_ambiguous_symbol_name_falls_back_to_unknown() -> None:
    service = TradeRepublicUniverseMatchingService(
        _StubClient(
            [
                {"source_last_refreshed_at": datetime(2026, 1, 1, 0, 0, 0)},
                [
                    {"isin": "X1", "instrument_name": "Test AG"},
                    {"isin": "X2", "instrument_name": "Test AG"},
                ],
            ]
        )
    )
    result = service.match_company(None, "TST", "Test AG")
    assert result.status == TR_STATUS_UNKNOWN


def test_analysis_service_trade_republic_filter() -> None:
    class _Repo:
        def fetch_trades(self, filters=None, limit=500):
            return pd.DataFrame(
                [
                    {"symbol_at_trade": "AAA", "trade_republic_universe_status": "IN_UNIVERSE", "trade_value_estimated": 1},
                    {"symbol_at_trade": "BBB", "trade_republic_universe_status": "UNKNOWN", "trade_value_estimated": 1},
                ]
            )

    service = AnalysisService(_Repo(), company_repo=None)  # type: ignore[arg-type]
    out = service.get_filtered_trades(filters={"trade_republic_universe_status": "IN_UNIVERSE"}, accumulate=False)
    assert len(out) == 1
    assert out.iloc[0]["symbol_at_trade"] == "AAA"
