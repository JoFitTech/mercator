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

    assert '"Legacy Trades": "Trades"' in source
    assert '"Trade-Detail"' in source
    assert 'return "Trades"' in source


def test_setup_phase_exports_stock_analysis_module_placeholders() -> None:
    models_source = _read("src/models/__init__.py")
    repositories_source = _read("src/db/repositories/__init__.py")
    services_source = _read("src/services/__init__.py")

    assert "STOCK_ANALYSIS_MODEL_MODULES" in models_source
    assert '"watchlist"' in models_source
    assert '"prediction"' in models_source

    assert "STOCK_ANALYSIS_REPOSITORY_MODULES" in repositories_source
    assert '"watchlist_repository"' in repositories_source
    assert '"data_quality_repository"' in repositories_source

    assert "STOCK_ANALYSIS_SERVICE_MODULES" in services_source
    assert '"stock_import_service"' in services_source
    assert '"preference_scoring_service"' in services_source
