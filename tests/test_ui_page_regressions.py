from __future__ import annotations

from datetime import date

import pandas as pd

from src.ui.pages.dashboard_page import _build_dashboard_filters
from src.ui.pages import dashboard_page
from src.services.import_service import ImportSummary
from src.ui.pages.admin_page import (
    _build_import_metrics,
    _build_import_success_message,
    _humanize_import_error,
    _public_share_status_message,
)
from src.app.navigation import public_share_sidebar_status_text
from src.app import navigation as app_navigation
from src.services.public_share_service import TunnelStatus
from src.ui.pages.trades_page import (
    TRADE_FILTER_DEFAULTS,
    _build_query_filters,
    _normalize_trades_filters,
)
from src.ui.components import page_scaffold


def test_build_dashboard_filters_handles_incomplete_range() -> None:
    assert _build_dashboard_filters((date(2026, 1, 1),)) == {
        "date_from": date(2026, 1, 1),
        "date_to": date(2026, 1, 1),
    }


def test_normalize_trades_filters_resets_invalid_direction() -> None:
    normalized = _normalize_trades_filters({"direction": "UP", "min_score": None, "min_value": None})
    assert normalized["direction"] == "Alle"
    assert normalized["min_score"] == 0
    assert normalized["min_value"] == 0


def test_build_query_filters_maps_direction_and_blank_values() -> None:
    filters = dict(TRADE_FILTER_DEFAULTS)
    filters.update({
        "symbol": "  AAPL ",
        "reporting_name": "  ",
        "direction": "SELL",
        "gate_status": "Alle",
        "validation_status": "VALID",
    })

    query = _build_query_filters(filters)

    assert query["symbol"] == "AAPL"
    assert query["reporting_name"] is None
    assert query["validation_status"] == "VALID"
    assert query["acquisition_or_disposition"] == "D"


def test_navigate_to_trades_sets_nav_target_and_reruns(monkeypatch) -> None:
    called = {"rerun": False}
    monkeypatch.setattr(dashboard_page.st, "session_state", {})

    def _fake_rerun() -> None:
        called["rerun"] = True

    monkeypatch.setattr(dashboard_page.st, "rerun", _fake_rerun)
    dashboard_page._navigate_to_trades()

    assert dashboard_page.st.session_state["nav_target"] == "Trades"
    assert called["rerun"] is True


def test_format_period_label_without_none_artifacts() -> None:
    label = dashboard_page._format_period_label({"date_from": date(2026, 4, 1), "date_to": None})
    assert "None" not in label
    assert label.startswith("ab ")


def test_humanize_import_error_masks_raw_sql_column_name() -> None:
    message = _humanize_import_error(Exception("1048 (23000): Column 'trade_republic_match_method' cannot be null"))
    assert "trade_republic_match_method" not in message
    assert "Import abgebrochen" in message


def test_humanize_import_error_maps_upstream_530_to_user_message() -> None:
    message = _humanize_import_error(Exception("Connection failed with status 530"))
    assert "HTTP 530" in message
    assert "UI bleibt verfügbar" in message


def test_invalid_nav_target_falls_back_to_dashboard(monkeypatch) -> None:
    monkeypatch.setattr(app_navigation.st, "session_state", {"nav_target": "invalid"})
    current = app_navigation.ensure_valid_nav_target()
    assert current == "Dashboard"
    assert app_navigation.st.session_state["nav_target"] == "Dashboard"


def test_sidebar_nav_target_is_not_overwritten_by_header_fallback() -> None:
    update = app_navigation._determine_header_nav_update(
        current_target="Admin",
        selected_header_target="Trades",
        previous_header_target="Trades",
    )
    assert update is None


def test_sidebar_nav_target_switches_when_header_selection_changes() -> None:
    update = app_navigation._determine_header_nav_update(
        current_target="Einstellungen",
        selected_header_target="Unternehmen",
        previous_header_target="Dashboard",
    )
    assert update == "Unternehmen"


def test_detail_nav_target_maps_to_parent_but_allows_header_switch() -> None:
    update = app_navigation._determine_header_nav_update(
        current_target="Trade-Detail",
        selected_header_target="Unternehmen",
        previous_header_target="Trades",
    )
    assert update == "Unternehmen"


def test_sidebar_widget_sync_resets_only_stale_header_value() -> None:
    assert app_navigation._should_reset_header_widget(
        current_target="Admin",
        widget_value="Dashboard",
        previous_header_target="Trades",
    ) is True
    assert app_navigation._should_reset_header_widget(
        current_target="Admin",
        widget_value="Trades",
        previous_header_target="Trades",
    ) is False
    assert app_navigation._should_reset_header_widget(
        current_target="Trades",
        widget_value="Dashboard",
        previous_header_target="Trades",
    ) is False


def test_admin_import_summary_helpers_include_new_profile_counters() -> None:
    summary = ImportSummary(
        fetched_feed_records=100,
        inserted_raw_records=88,
        upserted_clean_records=75,
        fetched_profiles=0,
        symbols_considered_for_enrichment=40,
        profile_fetch_attempts=0,
        profile_cache_hits=40,
        profile_failures=2,
    )

    message = _build_import_success_message(summary, force_profile_refresh=False)
    assert "Profile frisch geladen: 0" in message
    assert "Cache-Hits: 40" in message
    assert "Profilfehler: 2" in message

    metrics = dict(_build_import_metrics(summary))
    assert metrics["Enrichment-Kandidaten"] == 40
    assert metrics["Profile frisch geladen"] == 0
    assert metrics["Profile aus Cache"] == 40
    assert metrics["Profilfehler"] == 2


def test_dashboard_sector_chart_uses_vega_lite_without_plotly(monkeypatch) -> None:
    calls: list[dict] = []

    def _fake_vega_lite_chart(data, spec, **kwargs):  # noqa: ANN001
        calls.append({"data": data, "spec": spec, "kwargs": kwargs})

    monkeypatch.setattr(dashboard_page.st, "vega_lite_chart", _fake_vega_lite_chart)

    df = pd.DataFrame([
        {"sector": "Technology", "count": 3, "volume": 1_500_000},
        {"sector": "Unknown", "count": 1, "volume": 120_000},
    ])

    dashboard_page._render_sector_pie_chart(df)

    assert len(calls) == 1
    assert calls[0]["spec"]["mark"]["type"] == "arc"
    assert calls[0]["spec"]["encoding"]["theta"]["field"] == "count"
    assert calls[0]["kwargs"]["use_container_width"] is True


def test_dashboard_net_and_market_cap_charts_use_vega_lite(monkeypatch) -> None:
    calls: list[dict] = []

    def _fake_vega_lite_chart(data, spec, **kwargs):  # noqa: ANN001
        calls.append({"data": data, "spec": spec, "kwargs": kwargs})

    monkeypatch.setattr(dashboard_page.st, "vega_lite_chart", _fake_vega_lite_chart)

    net_df = pd.DataFrame([
        {"sector": "Technology", "delta": 4, "buy_count": 5, "sell_count": 1, "buy_volume": 5_000, "sell_volume": 2_000}
    ])
    cap_df = pd.DataFrame([{"bucket": "Large Cap", "companies": 12}])

    dashboard_page._render_net_sector_signal_chart(net_df)
    dashboard_page._render_market_cap_distribution_chart(cap_df)

    assert len(calls) == 2
    assert calls[0]["spec"]["mark"]["type"] == "bar"
    assert calls[0]["spec"]["encoding"]["x"]["field"] == "delta"
    assert calls[1]["spec"]["encoding"]["x"]["field"] == "companies"


def test_public_share_admin_status_messages_cover_running_stale_and_warning() -> None:
    assert _public_share_status_message(TunnelStatus.RUNNING) == ("success", "Tunnel läuft.")
    assert _public_share_status_message(TunnelStatus.STALE)[0] == "warning"
    assert "nicht erreichbar" in _public_share_status_message(TunnelStatus.WARNING)[1]


def test_public_share_sidebar_status_texts_cover_disabled_states() -> None:
    assert public_share_sidebar_status_text(TunnelStatus.STOPPED) == "Gestoppt"
    assert public_share_sidebar_status_text(TunnelStatus.ERROR) == "Fehler"
    assert public_share_sidebar_status_text(TunnelStatus.RUNNING) == "Läuft"


def test_safe_service_call_is_logic_only_without_direct_ui_rendering(monkeypatch) -> None:
    calls = {"error": 0, "expander": 0}

    monkeypatch.setattr(page_scaffold.st, "error", lambda *args, **kwargs: calls.__setitem__("error", calls["error"] + 1))
    monkeypatch.setattr(page_scaffold.st, "expander", lambda *args, **kwargs: calls.__setitem__("expander", calls["expander"] + 1))

    fallback, error = page_scaffold.safe_service_call(
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        context_label="Test",
        fallback={"ok": False},
    )

    assert fallback == {"ok": False}
    assert isinstance(error, RuntimeError)
    assert calls["error"] == 0
    assert calls["expander"] == 0


def test_dashboard_payload_error_hides_kpis(monkeypatch) -> None:
    class _SessionState(dict):
        def __getattr__(self, item):
            return self[item]

        def __setattr__(self, key, value):
            self[key] = value

    class _DashboardServiceStub:
        def build_dashboard_payload(self, filters: dict | None = None) -> dict:
            return {"payload_error_message": "Connection failed with status 530"}

    monkeypatch.setattr(dashboard_page.st, "session_state", _SessionState())
    monkeypatch.setattr(dashboard_page.st, "date_input", lambda *args, **kwargs: (date(2026, 1, 1), date(2026, 1, 2)))
    monkeypatch.setattr(dashboard_page.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(dashboard_page.st, "spinner", lambda *args, **kwargs: __import__("contextlib").nullcontext())
    monkeypatch.setattr(dashboard_page.st, "container", lambda *args, **kwargs: __import__("contextlib").nullcontext())
    monkeypatch.setattr(dashboard_page.st, "columns", lambda *args, **kwargs: [__import__("contextlib").nullcontext(), __import__("contextlib").nullcontext()])
    monkeypatch.setattr(dashboard_page.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard_page.st, "code", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard_page.st, "expander", lambda *args, **kwargs: __import__("contextlib").nullcontext())
    monkeypatch.setattr(dashboard_page, "render_page_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard_page, "summarize_filters", lambda *args, **kwargs: None)

    called = {"kpis": 0}
    monkeypatch.setattr(dashboard_page, "render_kpi_row", lambda *args, **kwargs: called.__setitem__("kpis", called["kpis"] + 1))

    dashboard_page.render_dashboard_page(service=_DashboardServiceStub(), import_service=None, settings=None, runtime_settings_service=None, db_status=None)

    assert called["kpis"] == 0
