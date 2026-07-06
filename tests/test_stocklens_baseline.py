"""Baseline guards for the brownfield StockLens migration phase.

These tests intentionally inspect current source wiring instead of importing the
Streamlit app. The setup phase must preserve the legacy app while migration
documentation and inventory work happens.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_current_streamlit_entrypoint_keeps_legacy_pages_wired() -> None:
    source = _read("streamlit_app.py")

    assert "from src.ui.pages.trades_page import render_trades_page" in source
    assert "from src.ui.pages.trade_detail_page import render_trade_detail_page" in source
    assert 'elif nav_target == "Trades":' in source
    assert 'elif nav_target == "Trade-Detail":' in source


def test_current_navigation_targets_preserve_legacy_trade_routes() -> None:
    source = _read("src/app/navigation.py")

    assert '"Trades": "Trades"' in source
    assert '"Trade-Detail"' in source
    assert 'return "Trades"' in source
