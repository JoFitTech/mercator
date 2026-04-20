"""Dashboard-Seite als signalorientierte Overview-Seite."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
<<<<<<< Updated upstream
=======
try:
    import plotly.express as px
except ModuleNotFoundError:
    px = None
>>>>>>> Stashed changes
import streamlit as st

from src.config.settings import AppSettings
from src.services.app_settings_service import AppSettingsService
from src.services.dashboard_service import DashboardService
from src.services.database_status_service import DatabaseStatus
from src.services.import_service import ImportService
from src.ui.components.page_scaffold import render_kpi_row, render_page_header
from src.ui.components.tables import render_dashboard_top_table


def _build_dashboard_filters(date_range: tuple[date, date] | list[date] | tuple[date, ...]) -> dict[str, date | None]:
    if isinstance(date_range, tuple | list):
        date_from = date_range[0] if len(date_range) > 0 else None
        date_to = date_range[1] if len(date_range) > 1 else date_from
    else:
        date_from = None
        date_to = None
    return {"date_from": date_from, "date_to": date_to}




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


def _navigate_to_trades() -> None:
    """Legacy-Helfer für bestehende Tests/Navigation."""
    st.session_state["nav_target"] = "Trades"
    st.rerun()

def _fmt_currency(value: float | int | None) -> str:
    if value is None:
        return "$0"
    return f"${float(value):,.0f}"


def _render_sector_pie_chart(df: pd.DataFrame) -> None:
    chart_df = df.copy()
    chart_df["tooltip_volume"] = chart_df.get("volume", 0).apply(_fmt_currency)
    chart_df["tooltip_count"] = chart_df.get("count", 0)
    st.vega_lite_chart(
        chart_df,
        {
            "mark": {"type": "arc", "outerRadius": 105},
            "encoding": {
                "theta": {"field": "count", "type": "quantitative"},
                "color": {"field": "sector", "type": "nominal", "legend": {"title": "Sektor"}},
                "tooltip": [
                    {"field": "sector", "type": "nominal", "title": "Sektor"},
                    {"field": "tooltip_count", "type": "quantitative", "title": "Trades"},
                    {"field": "tooltip_volume", "type": "nominal", "title": "Volumen"},
                ],
            },
            "view": {"stroke": None},
        },
        use_container_width=True,
    )


def _render_net_sector_signal_chart(df: pd.DataFrame) -> None:
    chart_df = df.copy()
    st.vega_lite_chart(
        chart_df,
        {
            "mark": {"type": "bar"},
            "encoding": {
                "y": {"field": "sector", "type": "nominal", "sort": "-x", "title": "Sektor"},
                "x": {"field": "delta", "type": "quantitative", "title": "Netto-Signal"},
                "color": {
                    "condition": {"test": "datum.delta >= 0", "value": "#5cb85c"},
                    "value": "#d9534f",
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
    st.vega_lite_chart(
        chart_df,
        {
            "mark": {"type": "bar"},
            "encoding": {
                "y": {"field": "bucket", "type": "nominal", "sort": "-x", "title": "Market-Cap Bucket"},
                "x": {"field": "companies", "type": "quantitative", "title": "Unternehmen"},
                "tooltip": [
                    {"field": "bucket", "type": "nominal", "title": "Bucket"},
                    {"field": "companies", "type": "quantitative", "title": "Unternehmen"},
                ],
            },
            "view": {"stroke": None},
        },
        use_container_width=True,
    )


def _navigate_to_trade(dedupe_key: str | None) -> None:
    if not dedupe_key:
        st.warning("Trade-Schlüssel fehlt für die Navigation.")
        return
    st.session_state["selected_trade_key"] = dedupe_key
    st.session_state["nav_target"] = "Trade-Detail"
    st.rerun()


def _navigate_to_company(symbol: str | None) -> None:
    if not symbol:
        st.warning("Symbol fehlt für die Navigation.")
        return
    st.session_state["selected_company_symbol"] = symbol
    st.session_state["nav_target"] = "Unternehmens-Detail"
    st.rerun()


def _render_missing_profile_actions(payload: dict, import_service: ImportService | None) -> None:
    missing_summary = payload.get("missing_data_summary", {})
    reasons_by_symbol = missing_summary.get("reasons_by_symbol", {})
    if not reasons_by_symbol:
        return

    st.markdown("#### Fehlende Profilinformationen")
    for symbol, reasons in reasons_by_symbol.items():
        col1, col2 = st.columns([0.9, 0.1], vertical_alignment="center")
        with col1:
            st.caption(f"**{symbol}:** {', '.join(reasons)}")
        with col2:
            if st.button("↻", key=f"refresh_profile_{symbol}", help=f"API2-Profil für {symbol} neu laden", use_container_width=True):
                if import_service is None:
                    st.warning("Reload aktuell nicht verfügbar (ImportService fehlt).")
                    continue
                result = import_service.refresh_company_profile_for_symbol(symbol)
                if result.get("ok"):
                    st.toast(result.get("message", "Profil aktualisiert."), icon="✅")
                    st.rerun()
                else:
                    st.warning(result.get("message", "Profil-Reload fehlgeschlagen."))


def _render_top_list(title: str, df: pd.DataFrame, table_key: str, side: str) -> None:
    st.markdown(f"#### {title}")
    event = render_dashboard_top_table(df, key=table_key)
    if not event or not event.get("selection") or not event["selection"].get("rows"):
        return

    selected_idx = int(event["selection"]["rows"][0])
    if selected_idx < 0 or selected_idx >= len(df):
        return

    selected_row = df.iloc[selected_idx]
    symbol = selected_row.get("symbol_at_trade")
    dedupe_key = selected_row.get("dedupe_key")

    if selected_row.get("profile_status") != "FETCHED":
        st.caption("Profil fehlt / unvollständig: API2 nicht geladen oder unvollständig.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Trade öffnen", key=f"open_trade_{side}", use_container_width=True):
            _navigate_to_trade(dedupe_key)
    with c2:
        if st.button("Unternehmen öffnen", key=f"open_company_{side}", use_container_width=True):
            _navigate_to_company(symbol)


def _show_plotly_fallback_notice() -> None:
    """Zeigt einmalig einen Hinweis, wenn Plotly im Runtime-Environment fehlt."""

    if px is not None:
        return
    if st.session_state.get("_plotly_fallback_notice_shown", False):
        return
    st.warning(
        "`plotly` ist in dieser Laufzeitumgebung nicht installiert. "
        "Charts werden als einfache Fallback-Darstellungen angezeigt."
    )
    st.session_state["_plotly_fallback_notice_shown"] = True


def render_dashboard_page(
    service: DashboardService | None,
    import_service: ImportService | None = None,
    settings: AppSettings | None = None,
    runtime_settings_service: AppSettingsService | None = None,
    db_status: DatabaseStatus | None = None,
) -> None:
    if service is None:
        st.warning("Dashboard derzeit nicht verfügbar, da MySQL nicht erreichbar ist.")
        return

    _show_plotly_fallback_notice()

    render_page_header("Markt-Dashboard", "Signalorientierter Überblick auf akkumulierter Basis.")

    if "dashboard_filters" not in st.session_state:
        st.session_state.dashboard_filters = {
            "date_range": (date.today() - timedelta(days=30), date.today())
        }

    with st.container(border=True):
        date_range = st.date_input(
            "Zeitraum",
            value=st.session_state.dashboard_filters["date_range"],
            format="DD.MM.YYYY",
        )
        st.session_state.dashboard_filters["date_range"] = date_range

    filters = _build_dashboard_filters(date_range)

    with st.spinner("Lade Dashboard..."):
        payload = service.build_dashboard_payload(filters=filters)

    kpis = [
        {"label": "Buy/Sell Verhältnis (Anzahl)", "value": payload.get("kpi_buy_sell_ratio_count", "0:0")},
        {"label": "Buy/Sell Verhältnis (Volumen)", "value": payload.get("kpi_buy_sell_ratio_volume", "0:0")},
        {
            "label": "Relevante Trades im Zeitraum",
            "value": str(payload.get("kpi_relevant_trades_count", 0)),
            "subtext": f"Gate PASS: {payload.get('gate_passed_count', 0)}",
        },
        {
            "label": "Betroffene Unternehmen",
            "value": str(payload.get("kpi_affected_companies_count", 0)),
            "subtext": (
                f"Profile vorhanden: {payload.get('fetched_profiles_count', 0)} / "
                f"Fehlend: {payload.get('missing_profiles_count', 0)}"
            ),
        },
        {"label": "Größter Buy", "value": _fmt_currency(payload.get("kpi_largest_buy_value", 0))},
        {"label": "Größter Sell", "value": _fmt_currency(payload.get("kpi_largest_sell_value", 0))},
    ]
    render_kpi_row(kpis)

    buy_sector_df = payload.get("sector_distribution_buy", pd.DataFrame())
    sell_sector_df = payload.get("sector_distribution_sell", pd.DataFrame())

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Buy-Sektoren-Verteilung")
        if buy_sector_df.empty:
            st.info("Keine BUY-Daten im Zeitraum.")
        else:
<<<<<<< Updated upstream
            _render_sector_pie_chart(buy_sector_df)
=======
            if px is not None:
                fig_buy = px.pie(
                    buy_sector_df,
                    names="sector",
                    values="count",
                    title=None,
                    hover_data=["volume"],
                )
                st.plotly_chart(fig_buy, use_container_width=True)
            else:
                fallback_buy = buy_sector_df.copy()
                if "sector" in fallback_buy.columns and "count" in fallback_buy.columns:
                    st.bar_chart(fallback_buy.set_index("sector")["count"])
                else:
                    st.dataframe(fallback_buy, use_container_width=True)
>>>>>>> Stashed changes
        st.caption(f"Gesamt Buy Volumen: {_fmt_currency(payload.get('total_buy_volume', 0))}")

    with c2:
        st.markdown("#### Sell-Sektoren-Verteilung")
        if sell_sector_df.empty:
            st.info("Keine SELL-Daten im Zeitraum.")
        else:
<<<<<<< Updated upstream
            _render_sector_pie_chart(sell_sector_df)
=======
            if px is not None:
                fig_sell = px.pie(
                    sell_sector_df,
                    names="sector",
                    values="count",
                    title=None,
                    hover_data=["volume"],
                )
                st.plotly_chart(fig_sell, use_container_width=True)
            else:
                fallback_sell = sell_sector_df.copy()
                if "sector" in fallback_sell.columns and "count" in fallback_sell.columns:
                    st.bar_chart(fallback_sell.set_index("sector")["count"])
                else:
                    st.dataframe(fallback_sell, use_container_width=True)
>>>>>>> Stashed changes
        st.caption(f"Gesamt Sell Volumen: {_fmt_currency(payload.get('total_sell_volume', 0))}")

    st.markdown("#### Netto-Sektor-Signal")
    net_sector_signal = payload.get("net_sector_signal", pd.DataFrame())
    if net_sector_signal.empty:
        st.info("Kein Netto-Sektor-Signal verfügbar.")
    else:
<<<<<<< Updated upstream
        _render_net_sector_signal_chart(net_sector_signal)
=======
        chart_df = net_sector_signal.copy()
        chart_df["signal_label"] = chart_df["delta"].apply(lambda x: f"{x:+.0f}")
        if px is not None:
            fig_net = px.bar(
                chart_df,
                x="delta",
                y="sector",
                orientation="h",
                color="delta",
                color_continuous_scale=["#d9534f", "#f0ad4e", "#5cb85c"],
                hover_data=["buy_count", "sell_count", "buy_volume", "sell_volume"],
            )
            fig_net.update_traces(text=chart_df["signal_label"], textposition="outside")
            st.plotly_chart(fig_net, use_container_width=True)
        else:
            if "sector" in chart_df.columns and "delta" in chart_df.columns:
                st.bar_chart(chart_df.set_index("sector")["delta"])
            st.dataframe(chart_df, use_container_width=True)
>>>>>>> Stashed changes

    st.markdown("#### Market-Cap-Verteilung")
    market_cap_df = payload.get("market_cap_distribution", pd.DataFrame())
    if market_cap_df.empty:
        st.info("Keine Market-Cap-Daten verfügbar.")
    else:
<<<<<<< Updated upstream
        _render_market_cap_distribution_chart(market_cap_df)
=======
        if px is not None:
            fig_market_cap = px.bar(
                market_cap_df,
                x="companies",
                y="bucket",
                orientation="h",
                text="companies",
                color="bucket",
            )
            fig_market_cap.update_layout(showlegend=False)
            st.plotly_chart(fig_market_cap, use_container_width=True)
        else:
            st.dataframe(market_cap_df, use_container_width=True)
>>>>>>> Stashed changes

    _render_missing_profile_actions(payload, import_service)

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
        st.caption(f"Letzte Datenaktualisierung: {payload['last_update']}")
