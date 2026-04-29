from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import src.data_sources.trade_republic_universe_source as source_module
from src.data_sources.trade_republic_universe_source import TradeRepublicUniverseSource


def test_source_loads_local_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "tr.csv"
    csv_file.write_text("isin,symbol,instrument_name\nUS0378331005,AAPL,Apple Inc.\n", encoding="utf-8")

    settings = SimpleNamespace(
        trade_republic_universe_local_csv=str(csv_file),
        project_root=tmp_path,
    )

    payload = TradeRepublicUniverseSource(settings).fetch()
    assert payload.source_type == "local_csv"
    assert payload.source_hash
    assert b"AAPL" in payload.content


def test_source_missing_local_csv_raises_clear_error(tmp_path: Path) -> None:
    settings = SimpleNamespace(
        trade_republic_universe_local_csv=str(tmp_path / "missing.csv"),
        project_root=tmp_path,
    )
    try:
        TradeRepublicUniverseSource(settings).fetch()
    except FileNotFoundError as exc:
        assert "nicht gefunden" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_source_empty_local_csv_raises_clear_error(tmp_path: Path) -> None:
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("\n", encoding="utf-8")

    settings = SimpleNamespace(
        trade_republic_universe_local_csv=str(csv_file),
        project_root=tmp_path,
    )
    try:
        TradeRepublicUniverseSource(settings).fetch()
    except ValueError as exc:
        assert "leer" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_source_module_has_no_requests_dependency() -> None:
    assert not hasattr(source_module, "requests")

