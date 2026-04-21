from __future__ import annotations

from datetime import date

import pandas as pd

from src.ui.pages.dashboard_page import _build_dashboard_filters
from src.ui.pages import dashboard_page
from src.ui.pages import trades_page
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
    _clamp_page as _clamp_trades_page,
    _normalize_trades_filters,
    _read_trade_filters_from_widgets,
    _reset_trade_filters_and_widgets,
    _trade_action_symbol_label,
)
from src.ui.pages.companies_page import _clamp_page as _clamp_companies_page, _company_display_name, _format_market_cap
from src.ui.pages import companies_page
from src.ui.components import tables as table_components
from src.ui.pages.company_detail_page import _safe_text as company_safe_text
from src.ui.pages.trade_detail_page import _safe_text as trade_safe_text
from src.ui.components import page_scaffold


def test_build_dashboard_filters_handles_incomplete_range() -> None:
    assert _build_dashboard_filters((date(2026, 1, 1),)) == {
        "date_from": date(2026, 1, 1),
        "date_to": date(2026, 1, 1),
    }


def test_build_dashboard_filters_handles_single_date_widget_value() -> None:
    assert _build_dashboard_filters(date(2026, 2, 1)) == {
        "date_from": date(2026, 2, 1),
        "date_to": date(2026, 2, 1),
    }


def test_dashboard_reset_filters_syncs_canonical_and_widget_state(monkeypatch) -> None:
    monkeypatch.setattr(
        dashboard_page.st,
        "session_state",
        {
            "dashboard_filters": {"date_range": (date(2026, 4, 1), date(2026, 4, 12))},
            "dashboard_filter_date_range": (date(2026, 4, 1), date(2026, 4, 12)),
        },
    )

    dashboard_page._reset_dashboard_filters_and_widgets()

    assert dashboard_page.st.session_state["dashboard_filters"]["date_range"] == dashboard_page.DASHBOARD_FILTER_DEFAULTS["date_range"]
    assert dashboard_page.st.session_state["dashboard_filter_date_range"] == dashboard_page.DASHBOARD_FILTER_DEFAULTS["date_range"]


def test_normalize_trades_filters_resets_invalid_direction() -> None:
    normalized = _normalize_trades_filters({"direction": "UP", "min_score": None, "min_value": None})
    assert normalized["direction"] == "Alle"
    assert normalized["min_score"] == 0
    assert normalized["min_value"] == 0


def test_normalize_trades_filters_accepts_single_date_and_sorts_range() -> None:
    single = _normalize_trades_filters({"date_range": date(2026, 1, 1)})
    assert single["date_range"] == (date(2026, 1, 1), date(2026, 1, 1))

    swapped = _normalize_trades_filters({"date_range": (date(2026, 2, 1), date(2026, 1, 1))})
    assert swapped["date_range"] == (date(2026, 1, 1), date(2026, 2, 1))


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


def test_trades_page_clamps_out_of_range_page() -> None:
    clamped, total_pages = _clamp_trades_page(current_page=9, total_rows=210, page_size=100)
    assert total_pages == 3
    assert clamped == 3


def test_companies_page_clamps_out_of_range_page() -> None:
    clamped, total_pages = _clamp_companies_page(current_page=5, total_rows=0, page_size=50)
    assert total_pages == 1
    assert clamped == 1


def test_trades_reset_filters_syncs_canonical_and_widget_state(monkeypatch) -> None:
    monkeypatch.setattr(
        trades_page.st,
        "session_state",
        {
            "trades_filters": {"symbol": "AAPL", "direction": "BUY"},
            "trades_filter_symbol": "AAPL",
            "trades_filter_direction": "BUY",
            "trades_filter_reporting_name": "Doe",
            "trades_filter_min_score": 33,
            "trades_filter_min_value": 200000,
        },
    )

    _reset_trade_filters_and_widgets()

    assert trades_page.st.session_state["trades_filters"]["symbol"] == ""
    assert trades_page.st.session_state["trades_filter_symbol"] == ""
    assert trades_page.st.session_state["trades_filter_direction"] == "Alle"
    assert trades_page.st.session_state["trades_filter_min_score"] == 0
    assert trades_page.st.session_state["trades_filter_min_value"] == 0


def test_trades_apply_reads_current_widget_values_without_enter(monkeypatch) -> None:
    monkeypatch.setattr(
        trades_page.st,
        "session_state",
        {
            "trades_filter_symbol": " msft ",
            "trades_filter_reporting_name": "  Jane Doe ",
            "trades_filter_direction": "BUY",
            "trades_filter_gate_status": "PASS",
            "trades_filter_validation_status": "VALID",
            "trades_filter_date_range": TRADE_FILTER_DEFAULTS["date_range"],
            "trades_filter_min_score": 50,
            "trades_filter_min_value": 123000,
        },
    )

    filters = _read_trade_filters_from_widgets()
    assert filters["symbol"] == "msft"
    assert filters["reporting_name"] == "Jane Doe"
    assert filters["direction"] == "BUY"
    assert filters["min_score"] == 50
    assert filters["min_value"] == 123000


def test_action_labels_use_fallbacks_instead_of_nan() -> None:
    trade_label = _trade_action_symbol_label(pd.Series({"symbol_at_trade": float("nan")}))
    company_label = _company_display_name(pd.Series({"company_name": float("nan"), "current_symbol": None}))
    assert trade_label == "Unbekanntes Symbol"
    assert company_label == "Unbekanntes Unternehmen"


def test_single_row_selection_parser_is_robust_for_invalid_payloads() -> None:
    assert table_components.get_single_selected_row_index(None, 3) is None
    assert table_components.get_single_selected_row_index({"selection": {"rows": []}}, 3) is None
    assert table_components.get_single_selected_row_index({"selection": {"rows": ["abc"]}}, 3) is None
    assert table_components.get_single_selected_row_index({"selection": {"rows": [99]}}, 3) is None
    assert table_components.get_single_selected_row_index({"selection": {"rows": [1]}}, 3) == 1


def test_dashboard_top_table_sort_prefers_value_then_date() -> None:
    df = pd.DataFrame([
        {"symbol_at_trade": "AAA", "accumulated_trade_value_estimated": 10, "trade_date": "2026-03-01"},
        {"symbol_at_trade": "BBB", "accumulated_trade_value_estimated": 50, "trade_date": "2026-03-02"},
        {"symbol_at_trade": "CCC", "accumulated_trade_value_estimated": 50, "trade_date": "2026-02-01"},
    ])
    sorted_df = table_components.sort_dashboard_top_rows(df)
    assert list(sorted_df["symbol_at_trade"]) == ["BBB", "CCC", "AAA"]


def test_trade_table_keeps_row_order_for_selection_mapping(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_dataframe(data, **kwargs):  # noqa: ANN001
        captured["rows"] = list(data["symbol_at_trade"])
        return {"selection": {"rows": [0]}}

    monkeypatch.setattr(table_components.st, "dataframe", _fake_dataframe)
    table_components.render_trade_table(pd.DataFrame([
        {"symbol_at_trade": "OLDER", "transaction_date": "2026-01-01"},
        {"symbol_at_trade": "NEWER", "transaction_date": "2026-03-01"},
    ]))

    assert captured["rows"] == ["OLDER", "NEWER"]


def test_ui_missing_values_are_sanitized_for_detail_and_company_views() -> None:
    assert company_safe_text("nan") == "Nicht verfügbar"
    assert trade_safe_text("None") == "Nicht verfügbar"
    assert _format_market_cap(None) == "Nicht verfügbar"


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


def test_missing_nav_target_is_initialized_to_dashboard(monkeypatch) -> None:
    monkeypatch.setattr(app_navigation.st, "session_state", {})
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


def test_companies_search_zero_results_shows_empty_state(monkeypatch) -> None:
    class _RepoStub:
        def list_active_companies(self, limit: int = 1000):  # noqa: ARG002
            return [
                {"company_name": "Apple Inc", "current_symbol": "AAPL", "trade_count": 4},
                {"company_name": "Microsoft", "current_symbol": "MSFT", "trade_count": 3},
            ]

    monkeypatch.setattr(companies_page, "render_page_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(companies_page, "render_kpi_row", lambda *args, **kwargs: None)
    monkeypatch.setattr(companies_page, "summarize_filters", lambda *args, **kwargs: None)
    monkeypatch.setattr(companies_page.st, "spinner", lambda *args, **kwargs: __import__("contextlib").nullcontext())
    monkeypatch.setattr(companies_page.st, "text_input", lambda *args, **kwargs: "does-not-exist")
    monkeypatch.setattr(companies_page.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(companies_page.st, "session_state", {})

    calls = {"empty_state": 0}
    monkeypatch.setattr(
        companies_page,
        "render_empty_state",
        lambda *args, **kwargs: calls.__setitem__("empty_state", calls["empty_state"] + 1),
    )

    companies_page.render_companies_page(repository=_RepoStub(), db_status=None)
    assert calls["empty_state"] == 1


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
