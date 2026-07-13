"""Rendert das Markt-Dashboard mit belastbaren KPIs, Charts und Top-Listen.

Die Datei wird gebraucht, um den wichtigsten Überblick für Entscheidungen zu liefern, ohne technische Diagnosewerte
oder Admin-Themen in die Hauptansicht zu mischen.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from src.config.settings import AppSettings
from src.services.app_settings_service import AppSettingsService
from src.services.dashboard_service import DashboardService
from src.services.database_status_service import DatabaseStatus
from src.services.import_service import ImportService
from src.ui.components.page_scaffold import (
    render_kpi_row,
    render_page_header,
    render_empty_state,
    safe_service_call,
    summarize_filters,
)
from src.ui.components.tables import get_single_selected_row_index, render_dashboard_top_table, sort_dashboard_top_rows
from src.ui.components.formatting import format_currency
from src.ui.ui_theme import CHART_PALETTE


def _coerce_dashboard_date_range(value: object) -> tuple[date, date]:
    if isinstance(value, date):
        return value, value
    if isinstance(value, (tuple, list)) and value:
        date_from = value[0] if isinstance(value[0], date) else DASHBOARD_FILTER_DEFAULTS["date_range"][0]
        second = value[1] if len(value) > 1 else date_from
        date_to = second if isinstance(second, date) else date_from
        if date_to < date_from:
            return date_to, date_from
        return date_from, date_to
    return DASHBOARD_FILTER_DEFAULTS["date_range"]


def _build_dashboard_filters(date_range: tuple[date, date] | list[date] | tuple[date, ...] | date) -> dict[str, date | None]:
    date_from, date_to = _coerce_dashboard_date_range(date_range)
    return {"date_from": date_from, "date_to": date_to}


DASHBOARD_FILTER_DEFAULTS = {
    "date_range": (date.today() - timedelta(days=30), date.today()),
}
DASHBOARD_WIDGET_RESYNC_PENDING_KEY = "dashboard_filters_resync_pending"
UNKNOWN_API2_SECTOR_LABEL = "Unknown / API2 fehlt"


def _normalize_dashboard_filters(filters: dict | None) -> dict:
    normalized = dict(DASHBOARD_FILTER_DEFAULTS)
    if filters:
        normalized.update(filters)
    normalized["date_range"] = _coerce_dashboard_date_range(normalized.get("date_range"))
    return normalized


def _sync_dashboard_filter_widgets_from_state(force: bool = False) -> None:
    active_filters = _normalize_dashboard_filters(st.session_state.get("dashboard_filters"))
    st.session_state["dashboard_filters"] = active_filters
    if force or "dashboard_filter_date_range" not in st.session_state:
        st.session_state["dashboard_filter_date_range"] = active_filters["date_range"]


def _read_dashboard_filters_from_widgets() -> dict:
    return _normalize_dashboard_filters({"date_range": st.session_state.get("dashboard_filter_date_range", DASHBOARD_FILTER_DEFAULTS["date_range"])})


def _reset_dashboard_filters_and_widgets() -> None:
    st.session_state["dashboard_filters"] = dict(DASHBOARD_FILTER_DEFAULTS)
    st.session_state[DASHBOARD_WIDGET_RESYNC_PENDING_KEY] = True
    st.session_state["dashboard_feedback"] = ("success", "Dashboard-Filter wurden auf den Standardzeitraum zurückgesetzt.")


def _format_period_label(filters: dict[str, date | None]) -> str:
    """Formatiert Zeitraum stabil im deutschen Datumsformat."""
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if date_from and date_to:
        return f"{date_from.strftime('%d.%m.%Y')} bis {date_to.strftime('%d.%m.%Y')}"
    if date_from:
        return f"ab {date_from.strftime('%d.%m.%Y')}"
    if date_to:
        return f"bis {date_to.strftime('%d.%m.%Y')}"
    return "Gesamter verfügbarer Zeitraum"


def _format_data_freshness_label(last_update: object) -> str:
    normalized = str(last_update or "").strip()
    if not normalized:
        return "Datenstand: —"
    return f"Datenstand bis {normalized}"


def _format_preference_metric(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _preference_ranking_rows(rankings: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in rankings:
        rows.append(
            {
                "rank": str(row.get("rank_position") or "-"),
                "symbol": str(row.get("symbol") or "-"),
                "preference_score": _format_preference_metric(row.get("preference_score")),
                "fundamental": _format_preference_metric(row.get("fundamental_component")),
                "technical": _format_preference_metric(row.get("technical_component")),
                "risk": _format_preference_metric(row.get("risk_component")),
                "prediction": _format_preference_metric(row.get("prediction_component")),
                "confidence": _format_preference_metric(row.get("confidence")),
                "uncertainty": _format_preference_metric(row.get("uncertainty")),
                "positive": str(row.get("explanation_positive") or "-"),
                "negative": str(row.get("explanation_negative") or "-"),
                "data_quality": str(row.get("data_quality_summary") or "-"),
            }
        )
    return rows


def _render_preference_rankings(rankings: list[dict[str, Any]]) -> None:
    st.markdown("#### Preference Ranking")
    st.caption("Transparentes Ranking der Watchlist. Keine Handels- oder Ausführungsentscheidung.")
    rows = _preference_ranking_rows(rankings)
    if not rows:
        st.info("Noch keine Preference Scores verfügbar.")
        return
    st.dataframe(rows, hide_index=True, use_container_width=True)


def _navigate_to_trades() -> None:
    """Legacy-Helfer für bestehende Tests/Navigation."""
    st.session_state["header_nav_target"] = "Trades"
    st.session_state["nav_target"] = "Trades"
    st.rerun()


def _is_unknown_or_api2_missing_sector(value: object) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in {
        "unknown",
        "unknown / api2 fehlt",
        "api2 fehlt/unknown",
        "api2 fehlt",
        "n/a",
    }


def _normalize_sector_label(value: object) -> str:
    normalized = str(value or "").strip()
    if not normalized or _is_unknown_or_api2_missing_sector(normalized):
        return UNKNOWN_API2_SECTOR_LABEL
    return normalized


def _build_sector_color_scale(*sector_frames: pd.DataFrame) -> dict[str, list[str]] | None:
    sectors: set[str] = set()
    for frame in sector_frames:
        if frame.empty or "sector" not in frame.columns:
            continue
        for raw_sector in frame["sector"].dropna().tolist():
            sector = _normalize_sector_label(raw_sector)
            if not sector or _is_unknown_or_api2_missing_sector(sector):
                continue
            sectors.add(sector)

    if not sectors:
        return None

    domain = sorted(sectors, key=lambda value: value.lower())
    palette = list(CHART_PALETTE.get("categorical", []))
    if not palette:
        return None
    range_colors = [palette[idx % len(palette)] for idx in range(len(domain))]
    return {"domain": domain, "range": range_colors}


def _render_sector_bar_chart(df: pd.DataFrame, color_scale: dict[str, list[str]] | None = None) -> None:
    """Rendert horizontales Balkendiagramm für Sektor-Verteilung."""
    chart_df = df.copy()
    sector_series = chart_df["sector"] if "sector" in chart_df.columns else pd.Series(["" for _ in range(len(chart_df))], index=chart_df.index)
    chart_df = chart_df[~sector_series.apply(_is_unknown_or_api2_missing_sector)]
    if chart_df.empty:
        st.info("Nur API2 fehlt/Unknown-Sektoren vorhanden; diese werden im Hauptchart ausgegliedert/ausgeblendet.")
        return

    color_encoding: dict[str, Any] = {"field": "sector", "type": "nominal", "title": "Sektor"}
    if color_scale:
        color_encoding["scale"] = color_scale

    st.vega_lite_chart(
        chart_df,
        {
            "mark": {"type": "bar"},
            "encoding": {
                "y": {"field": "sector", "type": "nominal", "sort": "-x", "title": "Sektor"},
                "x": {"field": "count", "type": "quantitative", "title": "Anzahl"},
                "color": color_encoding,
                "tooltip": [
                    {"field": "sector", "type": "nominal", "title": "Sektor"},
                    {"field": "count", "type": "quantitative", "title": "Anzahl"},
                    {"field": "volume", "type": "quantitative", "title": "Volumen"},
                ],
            },
            "view": {"stroke": None},
        },
        use_container_width=True,
    )


def _render_net_sector_signal_chart(df: pd.DataFrame) -> None:
    chart_df = df.copy()
    if "sector" not in chart_df.columns:
        chart_df["sector"] = UNKNOWN_API2_SECTOR_LABEL
    chart_df["sector"] = chart_df["sector"].apply(_normalize_sector_label)

    for column in ("buy_count", "sell_count", "buy_volume", "sell_volume"):
        if column not in chart_df.columns:
            chart_df[column] = 0
        chart_df[column] = pd.to_numeric(chart_df[column], errors="coerce").fillna(0)

    # Varianten wie "unknown" und "API2 fehlt" werden für das Netto-Signal zu einem Balken zusammengeführt.
    chart_df = (
        chart_df.groupby("sector", dropna=False)
        .agg(
            buy_count=("buy_count", "sum"),
            sell_count=("sell_count", "sum"),
            buy_volume=("buy_volume", "sum"),
            sell_volume=("sell_volume", "sum"),
        )
        .reset_index()
    )
    chart_df["delta"] = chart_df["buy_count"] - chart_df["sell_count"]
    chart_df = chart_df[~chart_df["sector"].apply(_is_unknown_or_api2_missing_sector)]
    chart_df = chart_df.sort_values(["delta", "buy_count"], ascending=[False, False])

    if chart_df.empty:
        st.info("Nur API2 fehlt/Unknown-Sektoren vorhanden; diese werden im Netto-Signal-Chart ausgeblendet.")
        return

    st.vega_lite_chart(
        chart_df,
        {
            "mark": {"type": "bar"},
            "encoding": {
                "y": {"field": "sector", "type": "nominal", "sort": "-x", "title": "Sektor"},
                "x": {"field": "delta", "type": "quantitative", "title": "Netto-Signal"},
                "color": {
                    "condition": {"test": "datum.delta >= 0", "value": CHART_PALETTE["positive"]},
                    "value": CHART_PALETTE["negative"],
                },
                "tooltip": [
                    {"field": "sector", "type": "nominal", "title": "Sektor"},
                    {"field": "delta", "type": "quantitative", "title": "Delta"},
                    {"field": "buy_count", "type": "quantitative", "title": "Buy Count"},
                    {"field": "sell_count", "type": "quantitative", "title": "Sell Count"},
                    {"field": "buy_volume", "type": "quantitative", "title": "Buy Volumen"},
                    {"field": "sell_volume", "type": "quantitative", "title": "Sell Volumen"},
                ],
            },
            "view": {"stroke": None},
        },
        use_container_width=True,
    )


def _render_market_cap_distribution_chart(df: pd.DataFrame) -> None:
    chart_df = df.copy()
    if "bucket" in chart_df.columns:
        chart_df = chart_df[~chart_df["bucket"].apply(_is_unknown_or_api2_missing_sector)]
    if chart_df.empty:
        st.info("Nur API2 fehlt/Unknown-Einträge vorhanden; diese werden im Verteilungs-Chart ausgeblendet.")
        return
    st.vega_lite_chart(
        chart_df,
        {
            "mark": {"type": "bar"},
            "encoding": {
                "y": {"field": "bucket", "type": "nominal", "sort": "-x", "title": "Market-Cap Bucket"},
                "x": {"field": "companies", "type": "quantitative", "title": "Unternehmen"},
                "color": {"field": "bucket", "type": "nominal", "legend": None, "scale": {"range": [CHART_PALETTE["neutral"], CHART_PALETTE["navy"], CHART_PALETTE["steel"], CHART_PALETTE["positive"]]}},
                "tooltip": [
                    {"field": "bucket", "type": "nominal", "title": "Bucket"},
                    {"field": "companies", "type": "quantitative", "title": "Unternehmen"},
                ],
            },
            "view": {"stroke": None},
        },
        use_container_width=True,
    )


def _navigate_to_trade_group(group_context: dict[str, object] | None) -> None:
    if not group_context:
        st.warning("Akkumulationsgruppe fehlt für die Navigation.")
        return
    st.session_state["selected_trade_group"] = group_context
    st.session_state.pop("selected_trade_key", None)
    st.session_state["nav_target"] = "Trade-Detail"
    st.rerun()


def _navigate_to_company(symbol: str | None) -> None:
    if not symbol:
        st.warning("Symbol fehlt für die Navigation.")
        return
    if str(symbol or "").strip():
        st.session_state["selected_company_symbol"] = str(symbol).strip()
        st.session_state["nav_target"] = "Unternehmens-Detail"
    st.rerun()


def _render_top_list(title: str, df: pd.DataFrame, table_key: str, side: str) -> None:
    st.markdown(f"#### {title}")
    view_df = sort_dashboard_top_rows(df)
    event = render_dashboard_top_table(view_df, key=table_key)
    selected_idx = get_single_selected_row_index(event, len(view_df))
    if selected_idx is None:
        return

    selected_row = view_df.iloc[selected_idx]
    symbol = str(selected_row.get("symbol_at_trade") or "").strip()
    if not symbol or symbol.lower() in {"nan", "none"}:
        symbol = "Unbekanntes Symbol"
    group_context = {
        "accumulation_group_id": selected_row.get("accumulation_group_id"),
        "symbol_at_trade": selected_row.get("symbol_at_trade"),
        "reporting_name": selected_row.get("reporting_name"),
        "direction": selected_row.get("direction"),
        "accumulation_start_date": selected_row.get("accumulation_start_date") or selected_row.get("trade_date"),
        "accumulation_end_date": selected_row.get("accumulation_end_date") or selected_row.get("trade_date"),
    }

    if selected_row.get("profile_status") != "FETCHED":
        st.caption("Profil fehlt / unvollständig: API2 nicht geladen oder unvollständig.")

    with st.container(border=True):
        st.markdown(f"**Ausgewählt:** {symbol}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Trade öffnen", key=f"open_trade_{side}_{selected_idx}", use_container_width=True):
                _navigate_to_trade_group(group_context)
        with c2:
            if st.button("Unternehmen öffnen", key=f"open_company_{side}_{selected_idx}", use_container_width=True):
                _navigate_to_company(symbol if symbol != "Unbekanntes Symbol" else None)


def render_dashboard_page(
    service: DashboardService | None,
    import_service: ImportService | None = None,
    settings: AppSettings | None = None,
    runtime_settings_service: AppSettingsService | None = None,
    db_status: DatabaseStatus | None = None,
) -> None:
    render_page_header(
        "Aktienanalyse-Übersicht",
        "Watchlist, Preference Ranking, Konfidenz und Datenqualität auf einen Blick.",
    )
    if service is None:
        st.warning("Dashboard derzeit nicht verfügbar, da MySQL nicht erreichbar ist.")
        return
    st.caption("Legacy-Zugriff während der Brownfield-Migration:")
    if st.button(
        "Legacy Trades öffnen",
        key="dashboard_open_trades_workspace",
        type="primary",
        use_container_width=False,
    ):
        _navigate_to_trades()
        return

    if "dashboard_filters" not in st.session_state:
        st.session_state["dashboard_filters"] = dict(DASHBOARD_FILTER_DEFAULTS)
    st.session_state["dashboard_filters"] = _normalize_dashboard_filters(st.session_state["dashboard_filters"])
    resync_pending = bool(st.session_state.pop(DASHBOARD_WIDGET_RESYNC_PENDING_KEY, False))
    _sync_dashboard_filter_widgets_from_state(force=resync_pending)

    with st.container(border=True):
        c_filter, c_reset = st.columns([0.8, 0.2], vertical_alignment="bottom")
        with c_filter:
            st.date_input(
                "Zeitraum (interaktiv)",
                key="dashboard_filter_date_range",
                format="DD.MM.YYYY",
            )
        with c_reset:
            if st.button("Filter zurücksetzen", use_container_width=True, key="dashboard_reset_filters"):
                _reset_dashboard_filters_and_widgets()
                st.rerun()
                return

    st.session_state["dashboard_filters"] = _read_dashboard_filters_from_widgets()
    feedback = st.session_state.pop("dashboard_feedback", None)
    if feedback:
        level, message = feedback
        if level == "success":
            st.success(message)
        elif level == "warning":
            st.warning(message)
        else:
            st.info(message)
    date_range = st.session_state["dashboard_filters"]["date_range"]

    filters = _build_dashboard_filters(date_range)
    summarize_filters("Aktive Filter", {"Zeitraum": _format_period_label(filters)})

    with st.spinner("Lade Dashboard..."):
        payload, load_error = safe_service_call(
            lambda: service.build_dashboard_payload(filters=filters),
            context_label="Dashboard-Daten",
            fallback={},
        )
    if load_error is not None:
        st.warning("Dashboard-Daten konnten aktuell nicht geladen werden. Bitte in wenigen Sekunden erneut versuchen.")
        with st.expander("Technische Details", expanded=False):
            st.code(str(load_error), language="text")
        return

    payload_error = str(payload.get("payload_error_message") or "").strip()
    if payload_error:
        st.warning("Datenquelle aktuell nicht erreichbar. Dashboard läuft im eingeschränkten Modus.")
        st.info("Kennzahlen werden vorübergehend ausgeblendet, bis die Datenquelle wieder verfügbar ist.")
        with st.expander("Technische Details", expanded=False):
            st.code(payload_error, language="text")
        return

    preference_rankings = payload.get("preference_rankings", [])
    preference_rows = _preference_ranking_rows(preference_rankings)
    preference_values = [
        float(row.get("preference_score"))
        for row in preference_rankings
        if isinstance(row.get("preference_score"), (int, float))
    ]
    confidence_values = [
        float(row.get("confidence"))
        for row in preference_rankings
        if isinstance(row.get("confidence"), (int, float))
    ]
    warning_count = sum(
        1
        for row in preference_rankings
        if str(row.get("data_quality_summary") or "").strip()
        and "all required" not in str(row.get("data_quality_summary") or "").lower()
    )
    stock_summary = payload.get("stock_analysis_summary") or {}
    open_quality_issues = int(stock_summary.get("open_data_quality_issues") or warning_count)
    render_kpi_row(
        [
            {"label": "Aktive Watchlist", "value": str(stock_summary.get("watchlist_active") or 0)},
            {"label": "Bewertete Aktien", "value": str(len(preference_rows))},
            {"label": "Top Preference", "value": f"{max(preference_values):.2f}" if preference_values else "-"},
            {
                "label": "Ø Konfidenz",
                "value": f"{sum(confidence_values) / len(confidence_values):.2f}" if confidence_values else "-",
            },
            {"label": "Offene Datenqualitätsprobleme", "value": str(open_quality_issues)},
        ]
    )
    _render_preference_rankings(preference_rankings)
    st.markdown("### Legacy: Insider-Trade-Auswertung")
    st.caption("Dieser Abschnitt bleibt bis zum abgeschlossenen Kompatibilitäts-Cleanup verfügbar.")

    avg_score = payload.get("avg_score")
    avg_score_label = "-"
    if isinstance(avg_score, (int, float)):
        avg_score_label = f"{float(avg_score):.2f}"
    elif isinstance(avg_score, str):
        try:
            avg_score_label = f"{float(avg_score):.2f}"
        except ValueError:
            avg_score_label = "-"
    kpis = [
        {"label": "Auswertbare Trades", "value": str(payload.get("kpi_relevant_trades_count", 0))},
        {"label": "Aktive Unternehmen", "value": str(payload.get("kpi_affected_companies_count", 0))},
        {"label": "Ø Score", "value": avg_score_label},
        {"label": "Buy-Volumen", "value": format_currency(payload.get("total_buy_volume", 0))},
    ]
    render_kpi_row(kpis)

    with st.container(border=True):
        st.caption(
            f"Zeitraum: {_format_period_label(filters)} | {_format_data_freshness_label(payload.get('last_update'))}"
        )
    if payload.get("kpi_relevant_trades_count", 0) == 0:
        render_empty_state(
            "Für den ausgewählten Zeitraum liegen keine auswertbaren Trades vor. "
            "Bitte Zeitraum erweitern oder Filter zurücksetzen."
        )

    buy_sector_df = payload.get("sector_distribution_buy", pd.DataFrame())
    sell_sector_df = payload.get("sector_distribution_sell", pd.DataFrame())
    sector_color_scale = _build_sector_color_scale(buy_sector_df, sell_sector_df)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Buy-Sektoren")
        if buy_sector_df.empty:
            st.info("Keine BUY-Daten im Zeitraum.")
        else:
            _render_sector_bar_chart(buy_sector_df, color_scale=sector_color_scale)
        st.caption(f"Gesamt Buy Volumen: {format_currency(payload.get('total_buy_volume', 0))}")

    with c2:
        st.markdown("#### Sell-Sektoren")
        if sell_sector_df.empty:
            st.info("Keine SELL-Daten im Zeitraum.")
        else:
            _render_sector_bar_chart(sell_sector_df, color_scale=sector_color_scale)
        st.caption(f"Gesamt Sell Volumen: {format_currency(payload.get('total_sell_volume', 0))}")

    unknown_buy = int(buy_sector_df[buy_sector_df.get("sector", "").apply(_is_unknown_or_api2_missing_sector)]["count"].sum()) if not buy_sector_df.empty and "sector" in buy_sector_df.columns and "count" in buy_sector_df.columns else 0
    unknown_sell = int(sell_sector_df[sell_sector_df.get("sector", "").apply(_is_unknown_or_api2_missing_sector)]["count"].sum()) if not sell_sector_df.empty and "sector" in sell_sector_df.columns and "count" in sell_sector_df.columns else 0
    if unknown_buy or unknown_sell:
        st.caption(f"Hinweis: {unknown_buy} BUY und {unknown_sell} SELL ohne belastbare API2-Sektorzuordnung sind im Hauptchart ausgeblendet.")

    st.markdown("#### Netto-Sektor-Signal")
    st.caption("Positiv = BUY-Überhang, negativ = SELL-Überhang im gewählten Zeitraum.")
    net_sector_signal = payload.get("net_sector_signal", pd.DataFrame())
    if net_sector_signal.empty:
        st.info("Kein Netto-Sektor-Signal verfügbar.")
    else:
        _render_net_sector_signal_chart(net_sector_signal)

    st.markdown("#### Market-Cap-Verteilung")
    st.caption("Zeigt die Anzahl betroffener Unternehmen pro Größenklasse.")
    market_cap_df = payload.get("market_cap_distribution", pd.DataFrame())
    if market_cap_df.empty:
        st.info("Keine Market-Cap-Daten verfügbar.")
    else:
        _render_market_cap_distribution_chart(market_cap_df)
    st.caption("Hinweis: B = Billion (englisch) = Milliarde (deutsch). Beispiel: 2B = 2 Milliarden USD.")


    top_buys = payload.get("top_buys", pd.DataFrame())
    top_sells = payload.get("top_sells", pd.DataFrame())

    if "trade_date" in top_buys.columns:
        top_buys = top_buys.copy()
        top_buys["trade_date"] = pd.to_datetime(top_buys["trade_date"], errors="coerce")
    if "trade_date" in top_sells.columns:
        top_sells = top_sells.copy()
        top_sells["trade_date"] = pd.to_datetime(top_sells["trade_date"], errors="coerce")

    b1, b2 = st.columns(2)
    with b1:
        _render_top_list("Top 5 Buys", top_buys, table_key="dashboard_top_buys", side="buy")
    with b2:
        _render_top_list("Top 5 Sells", top_sells, table_key="dashboard_top_sells", side="sell")

    if payload.get("last_update"):
        st.caption(f"Hinweis: {_format_data_freshness_label(payload['last_update'])}.")
