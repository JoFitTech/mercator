from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from src.services.analysis_service import AnalysisService
from src.services.import_service import ImportService
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
        self.committed = False

    def cursor(self, **_kwargs):
        return _StubCursor(self._scripted)

    def commit(self):
        self.committed = True

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


def test_parse_universe_csv_semicolon_dialect() -> None:
    payload = "isin;symbol;instrument_name\nDE000BASF111;BASF;BASF SE\n"
    parsed = TradeRepublicUniverseIngestionService.parse_universe_csv(payload)
    assert parsed.valid_rows == 1
    assert parsed.instruments[0].isin == "DE000BASF111"
    assert parsed.instruments[0].symbol == "BASF"


def test_parse_universe_csv_aliased_columns() -> None:
    payload = "ISIN,Ticker,Name\nUS0378331005,AAPL,Apple Inc.\n"
    parsed = TradeRepublicUniverseIngestionService.parse_universe_csv(payload)
    assert parsed.valid_rows == 1
    assert parsed.instruments[0].isin == "US0378331005"
    assert parsed.instruments[0].symbol == "AAPL"
    assert parsed.instruments[0].instrument_name == "Apple Inc."


def test_parse_universe_csv_filters_invalid_rows() -> None:
    payload = "isin,symbol,instrument_name,country,type\nDE000BASF111,BASF,BASF SE,DE,Stock\n,,Broken,DE,Stock\n"
    parsed = TradeRepublicUniverseIngestionService.parse_universe_csv(payload)
    assert parsed.valid_rows == 1
    assert parsed.invalid_rows == 1
    assert parsed.instruments[0].isin == "DE000BASF111"


def test_parse_universe_csv_empty_source() -> None:
    parsed = TradeRepublicUniverseIngestionService.parse_universe_csv("")
    assert parsed.total_rows == 0
    assert parsed.instruments == []


def test_parse_universe_csv_unexpected_format() -> None:
    parsed = TradeRepublicUniverseIngestionService.parse_universe_csv("not,a,real\nbut-no-isin")
    assert parsed.valid_rows == 0
    assert parsed.total_rows >= 1


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


def test_import_local_csv_handles_missing_file(tmp_path: Path) -> None:
    settings = SimpleNamespace(
        project_root=tmp_path,
        trade_republic_universe_local_csv="missing.csv",
        trade_republic_refresh_ttl_hours=24,
    )
    service = TradeRepublicUniverseIngestionService(settings=settings, mysql_client=_StubClient([]))  # type: ignore[arg-type]
    summary = service.import_local_csv(force=True)
    assert summary.status == "refresh_failed"
    assert "nicht gefunden" in str(summary.error)


def test_import_local_csv_fails_when_no_valid_isins(tmp_path: Path) -> None:
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text("isin,symbol,instrument_name\nBAD,AAPL,Apple Inc.\n", encoding="utf-8")

    settings = SimpleNamespace(
        project_root=tmp_path,
        trade_republic_universe_local_csv=str(csv_file),
        trade_republic_refresh_ttl_hours=24,
    )
    service = TradeRepublicUniverseIngestionService(settings=settings, mysql_client=_StubClient([]))  # type: ignore[arg-type]

    summary = service.import_local_csv(force=True)

    assert summary.status == "refresh_failed"
    assert "keine gültigen Instrumente" in str(summary.error)


def test_normal_import_does_not_trigger_trade_republic_refresh() -> None:
    class _FmpClient:
        def fetch_latest_insider_trades(self, page=0, limit=100):
            return []

    class _RawRepo:
        def upsert_raw_trades(self, rows):
            return len(rows)

    class _CompanyMongoRepo:
        pass

    class _TrIngestion:
        def __init__(self) -> None:
            self.calls = 0

        def refresh_if_stale(self, force: bool = False):
            self.calls += 1
            return True, "refreshed"

    tr_ingestion = _TrIngestion()
    service = ImportService(
        fmp_client=_FmpClient(),  # type: ignore[arg-type]
        gate_evaluator=type("_Gate", (), {"evaluate": lambda self, item: type("_Decision", (), {"status": "PASS", "reason": None})()})(),  # type: ignore[arg-type]
        raw_repo=_RawRepo(),  # type: ignore[arg-type]
        company_mongo_repo=_CompanyMongoRepo(),  # type: ignore[arg-type]
        trade_mysql_repo=None,
        company_mysql_repo=None,
        tr_ingestion_service=tr_ingestion,  # type: ignore[arg-type]
    )

    service.run_hourly_import()

    assert tr_ingestion.calls == 0
