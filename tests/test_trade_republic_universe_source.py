from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.data_sources.trade_republic_universe_source import TradeRepublicUniverseSource


def test_source_loads_local_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "tr.csv"
    csv_file.write_text("isin,symbol,instrument_name\nUS0378331005,AAPL,Apple Inc.\n", encoding="utf-8")

    settings = SimpleNamespace(
        trade_republic_universe_source_mode="local_csv",
        trade_republic_universe_local_csv=str(csv_file),
        project_root=tmp_path,
    )

    payload = TradeRepublicUniverseSource(settings).fetch()
    assert payload.source_type == "local_csv"
    assert payload.source_hash
    assert b"AAPL" in payload.content


def test_source_blocks_remote_when_disabled() -> None:
    settings = SimpleNamespace(
        trade_republic_universe_source_mode="remote_csv",
        trade_republic_allow_remote_refresh=False,
        trade_republic_universe_url="https://example.test/universe.csv",
    )
    try:
        TradeRepublicUniverseSource(settings).fetch()
    except PermissionError as exc:
        assert "deaktiviert" in str(exc)
    else:
        raise AssertionError("Expected PermissionError")

