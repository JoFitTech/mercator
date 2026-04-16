"""Explorer-Seite mit interaktiven Filtern auf bereinigte Trades."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.services.analysis_service import AnalysisService
from src.services.app_settings_service import AppSettingsService
from src.ui.components.context_bar import render_context_bar
from src.ui.components.status_badges import score_class_badge, status_badge


PRIMARY_DIRECTIONS = ["Alle", "BUY", "SELL"]


def _safe_select_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    safe_df = frame.copy()
    for col in columns:
        if col not in safe_df.columns:
            safe_df[col] = pd.NA
    return safe_df[columns]


def _default_filters() -> dict[str, Any]:
    return {
        "symbol": "",
        "reporting_name": "",
        "direction": "Alle",
        "min_value": 100_000,
        "limit": 1000,
        "accumulate": True,
        "show_raw": False,
        "gate_statuses": ["PASS", "PENDING", "FAIL"],
        "validation_statuses": ["VALID", "INVALID", "UNCHECKED"],
    }


def _render_filter_summary(filters: dict[str, Any]) -> None:
    parts: list[str] = []
    if filters.get("symbol"):
        parts.append(f"Ticker: **{filters['symbol']}**")
    if filters.get("reporting_name"):
        parts.append(f"Insider: **{filters['reporting_name']}**")
    if filters.get("direction") != "Alle":
        parts.append(f"Richtung: **{filters['direction']}**")
    if int(filters.get("min_value", 0)) > 0:
        parts.append(f"Min. Trade Value: **${int(filters['min_value']):,}**")
    if filters.get("gate_statuses") and len(filters["gate_statuses"]) < 3:
        parts.append(f"Gate: **{', '.join(filters['gate_statuses'])}**")
    if filters.get("validation_statuses") and len(filters["validation_statuses"]) < 3:
        parts.append(f"Validation: **{', '.join(filters['validation_statuses'])}**")

    st.caption("Aktive Filter: " + (" · ".join(parts) if parts else "Keine (Standardansicht)"))


from src.ui.components.tables import render_smart_table

def render_explorer_page(service: AnalysisService, settings_service: AppSettingsService | None = None) -> None:
    """Rendert Filter und Screener-Tabelle für Insider-Trades."""
    st.title("Trades")
    st.caption("Fokussierter Screener für Trade-Relevanz und Richtung.")

    defaults = _default_filters()
    
    # 1. Zentrale State-Initialisierung (Persistent / Applied State)
    if "explorer_filters" not in st.session_state:
        if settings_service is not None:
            persisted = settings_service.load_filter("explorer", "filters", defaults)
            st.session_state.explorer_filters = persisted if isinstance(persisted, dict) else defaults.copy()
        else:
            st.session_state.explorer_filters = defaults.copy()
    
    # Context Bar rendern
    filters_state = st.session_state.explorer_filters
    active_chips = []
    if filters_state.get("symbol"): active_chips.append(f"Ticker: {filters_state['symbol']}")
    if filters_state.get("direction") != "Alle": active_chips.append(f"Richtung: {filters_state['direction']}")
    if int(filters_state.get("min_value", 0)) > 100000: active_chips.append(f">{int(filters_state['min_value']):,}")
    
    render_context_bar(
        active_filters=active_chips if active_chips else ["Standardansicht"],
        mysql_target=st.session_state.get("mysql_runtime_target", "local")
    )

    # Reset-Logik
    def do_reset():
        st.session_state.explorer_filters = defaults.copy()
        if settings_service is not None:
            settings_service.save_filter("explorer", "filters", st.session_state.explorer_filters)
        # Wir verzichten auf explizites Widget-Key-Setting hier, um Exceptions zu vermeiden.
        # Streamlit wird beim Rerun die Widgets neu laden.

    # 3. Layout: Golden Ratio (ca. 35/65 Split)
    filter_col, result_col = st.columns([0.30, 0.70], gap="large")

    with filter_col:
        with st.form("explorer_filters_form", border=True):
            st.subheader("Filter")
            
            symbol = st.text_input(
                "Ticker", 
                value=st.session_state.explorer_filters.get("symbol", ""),
                placeholder="z. B. AAPL",
                help="Suche nach Ticker (z.B. AAPL, TSLA). Eingabe wird durch 'Filter anwenden' übernommen.",
            )
            reporting = st.text_input(
                "Insider (Name)", 
                value=st.session_state.explorer_filters.get("reporting_name", ""),
                placeholder="z. B. Tim Cook",
            )
            
            direction = st.selectbox(
                "Richtung",
                PRIMARY_DIRECTIONS,
                index=PRIMARY_DIRECTIONS.index(st.session_state.explorer_filters.get("direction", "Alle")),
            )
            
            min_value = st.number_input(
                "Min. Trade Value ($)",
                min_value=0,
                value=int(st.session_state.explorer_filters.get("min_value", 100000)),
                step=50_000,
            )

            with st.expander("Status & Details", expanded=False):
                limit = st.select_slider(
                    "Max. Zeilen", 
                    options=[250, 500, 1000, 2000], 
                    value=st.session_state.explorer_filters.get("limit", 1000)
                )
                accumulate = st.toggle(
                    "Trades akkumulieren", 
                    value=st.session_state.explorer_filters.get("accumulate", True),
                    help="Fasst Trades desselben Insiders innerhalb von 3 Tagen zusammen."
                )
                show_raw = st.toggle(
                    "Einzeltrades anzeigen", 
                    value=st.session_state.explorer_filters.get("show_raw", False),
                )

                gate_statuses = st.multiselect(
                    "Gate-Status",
                    options=["PASS", "PENDING", "FAIL"],
                    default=st.session_state.explorer_filters.get("gate_statuses", ["PASS", "PENDING", "FAIL"])
                )
                validation_statuses = st.multiselect(
                    "Validation",
                    options=["VALID", "INVALID", "UNCHECKED"],
                    default=st.session_state.explorer_filters.get("validation_statuses", ["VALID", "INVALID", "UNCHECKED"])
                )

            apply_filters = st.form_submit_button("Filter anwenden", type="primary", use_container_width=True)
            st.form_submit_button("Zurücksetzen", use_container_width=True, on_click=do_reset)

            if apply_filters:
                st.session_state.explorer_filters.update(
                    {
                        "symbol": symbol.strip().upper(),
                        "reporting_name": reporting.strip(),
                        "direction": direction,
                        "min_value": int(min_value),
                        "limit": int(limit),
                        "accumulate": bool(accumulate),
                        "show_raw": bool(show_raw),
                        "gate_statuses": gate_statuses if gate_statuses else ["PASS", "PENDING", "FAIL"],
                        "validation_statuses": validation_statuses if validation_statuses else ["VALID", "INVALID", "UNCHECKED"],
                    }
                )
                if settings_service is not None:
                    settings_service.save_filter("explorer", "filters", st.session_state.explorer_filters)
                st.rerun()

    with result_col:
        filters_state = st.session_state.explorer_filters
        _render_filter_summary(filters_state)

        api_direction = None
        if filters_state["direction"] == "BUY":
            api_direction = "A"
        elif filters_state["direction"] == "SELL":
            api_direction = "D"

        query_filters = {
            "symbol": filters_state["symbol"] or None,
            "reporting_name": filters_state["reporting_name"] or None,
            "acquisition_or_disposition": api_direction,
        }

        data = service.get_filtered_trades(
            filters=query_filters,
            limit=int(filters_state.get("limit", 1000)),
            accumulate=bool(filters_state.get("accumulate", True)) and not bool(filters_state.get("show_raw", False)),
            min_value=float(filters_state.get("min_value", 0)),
        )

        if data.empty:
            st.info("Keine Treffer für die aktuelle Filterkombination.")
            return

        # Explizite Nachfilterung der Richtung (Finding 2: Guard gegen inkonsistente Repo/Agg-Ergebnisse)
        if filters_state["direction"] != "Alle" and "direction" in data.columns:
            data = data[data["direction"] == filters_state["direction"]]

        if "gate_status" in data.columns:
            data = data[data["gate_status"].fillna("UNKNOWN").astype(str).str.upper().isin(filters_state["gate_statuses"])]
        if "validation_status" in data.columns:
            data = data[data["validation_status"].fillna("UNKNOWN").astype(str).str.upper().isin(filters_state["validation_statuses"])]

        if data.empty:
            st.info("Keine Treffer nach Gate-/Validation-Filter.")
            return

        score_col = "score" if "score" in data.columns else None
        value_col = "accumulated_trade_value_estimated" if "accumulated_trade_value_estimated" in data.columns else "trade_value_estimated"
        if score_col is not None:
            data = data.sort_values(by=[score_col, value_col], ascending=[False, False], na_position="last")

        # KPI Zeile (Spec: max 5)
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Treffer", f"{len(data):,}")
        k2.metric("BUY", f"{int((data.get('direction', pd.Series(dtype='object')) == 'BUY').sum()):,}")
        k3.metric("Gate PASS", f"{int((data.get('gate_status', pd.Series(dtype='object')).astype(str).str.upper() == 'PASS').sum()):,}")
        k4.metric("Ø Score", f"{pd.to_numeric(data.get('score'), errors='coerce').mean():.1f}" if "score" in data.columns else "-")
        
        # BUY-Quote als 5. KPI (Spec Konformität)
        buy_count = int((data.get('direction', pd.Series(dtype='object')) == 'BUY').sum())
        total_count = len(data)
        k5.metric("BUY-Quote", f"{(buy_count/total_count):.0%}" if total_count > 0 else "-")

        st.subheader("Trade-Arbeitsfläche")

        if filters_state["accumulate"] and not filters_state["show_raw"]:
            display_df = _safe_select_columns(
                data,
                [
                    "symbol_at_trade",
                    "direction",
                    "score",
                    "score_class",
                    "score_status",
                    "accumulated_trade_value_estimated",
                    "gate_status",
                    "validation_status",
                    "transaction_date",
                    "company_name",
                    "reporting_name",
                    "accumulated_qty",
                    "accumulated_avg_price_weighted",
                    "accumulated_trade_count",
                ],
            ).copy()
            display_df["accumulated_trade_count"] = pd.to_numeric(display_df["accumulated_trade_count"], errors="coerce").fillna(1)

            table_columns = [
                "symbol_at_trade",
                "direction",
                "score",
                "score_class",
                "score_status",
                "accumulated_trade_value_estimated",
                "gate_status",
                "validation_status",
                "transaction_date",
                "company_name",
                "reporting_name",
                "accumulated_trade_count",
                "accumulated_qty",
                "accumulated_avg_price_weighted",
            ]

            col_config = {
                "symbol_at_trade": st.column_config.TextColumn("Ticker", width="small"),
                "direction": st.column_config.TextColumn("Richtung", width="small"),
                "score": st.column_config.NumberColumn("Score", format="%.2f", width="small"),
                "score_class": st.column_config.TextColumn("Klasse", width="small"),
                "score_status": st.column_config.TextColumn("Status", width="small"),
                "accumulated_trade_value_estimated": st.column_config.NumberColumn("Trade Value", format="$%.2f", width="medium"),
                "gate_status": st.column_config.TextColumn("Gate", width="small"),
                "validation_status": st.column_config.TextColumn("Validation", width="small"),
                "transaction_date": st.column_config.DateColumn("Datum", width="small"),
                "company_name": st.column_config.TextColumn("Unternehmen", width="large"),
                "reporting_name": st.column_config.TextColumn("Insider", width="medium"),
                "accumulated_trade_count": st.column_config.NumberColumn("#Trades", format="%d", width="small"),
                "accumulated_qty": st.column_config.NumberColumn("Stück", format="%d"),
                "accumulated_avg_price_weighted": st.column_config.NumberColumn("Ø Preis", format="$%.2f"),
            }
        else:
            display_df = _safe_select_columns(
                data,
                [
                    "symbol_at_trade",
                    "direction",
                    "score",
                    "score_class",
                    "score_status",
                    "trade_value_estimated",
                    "gate_status",
                    "validation_status",
                    "transaction_date",
                    "company_name",
                    "reporting_name",
                    "qty",
                    "price",
                ],
            ).copy()

            table_columns = [
                "symbol_at_trade",
                "direction",
                "score",
                "score_class",
                "score_status",
                "trade_value_estimated",
                "gate_status",
                "validation_status",
                "transaction_date",
                "company_name",
                "reporting_name",
                "qty",
                "price",
            ]
            col_config = {
                "symbol_at_trade": st.column_config.TextColumn("Ticker", width="small"),
                "direction": st.column_config.TextColumn("Richtung", width="small"),
                "score": st.column_config.NumberColumn("Score", format="%.2f", width="small"),
                "score_class": st.column_config.TextColumn("Klasse", width="small"),
                "score_status": st.column_config.TextColumn("Status", width="small"),
                "trade_value_estimated": st.column_config.NumberColumn("Trade Value", format="$%.2f", width="medium"),
                "gate_status": st.column_config.TextColumn("Gate", width="small"),
                "validation_status": st.column_config.TextColumn("Validation", width="small"),
                "transaction_date": st.column_config.DateColumn("Datum", width="small"),
                "company_name": st.column_config.TextColumn("Unternehmen", width="large"),
                "reporting_name": st.column_config.TextColumn("Insider", width="medium"),
                "qty": st.column_config.NumberColumn("Stück", format="%d"),
                "price": st.column_config.NumberColumn("Preis", format="$%.2f"),
            }

        event = render_smart_table(
            display_df[table_columns],
            column_config=col_config,
            height=560,
            on_select="rerun",
            selection_mode="single-row",
        )

        if event and event.get("selection") and event["selection"].get("rows"):
            selected_row_idx = event["selection"]["rows"][0]
            selected_ticker = display_df.iloc[selected_row_idx]["symbol_at_trade"]
            st.session_state["selected_ticker"] = selected_ticker
            st.success(f"Ausgewählt: **{selected_ticker}**. Gehe zur 'Detailansicht' für eine vollständige Analyse.")

        # Quick Drilldown (Spec: Zahlen müssen lesbar sein)
        symbols = sorted({str(v) for v in display_df.get("symbol_at_trade", pd.Series(dtype="object")).dropna().tolist()})
        if symbols:
            st.markdown("---")
            st.subheader("Quick Drilldown")
            
            # Falls kein Ticker selektiert wurde, nimm den ersten
            current_selection = st.session_state.get("selected_ticker")
            if current_selection not in symbols:
                current_selection = symbols[0]
            
            selected_symbol = st.selectbox(
                "Kontextvorschau für Ticker",
                options=symbols,
                index=symbols.index(current_selection) if current_selection in symbols else 0,
            )
            
            detail = service.get_ticker_detail(selected_symbol, accumulate=True)
            profile = detail.company_profile or {}
            
            with st.container(border=True):
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("Trades", f"{int(detail.metrics.get('trade_count') or 0):,}")
                avg_price = detail.metrics.get("avg_price")
                d2.metric("Ø Preis", f"${float(avg_price):,.2f}" if avg_price is not None else "-")
                
                # Status mit Badge statt Metric (Spec)
                with d3:
                    st.write("**Bewertung**")
                    score_class_badge(detail.metrics.get("score_class", "F"))
                
                with d4:
                    st.write("**Gate**")
                    status_badge(detail.metrics.get("overall_status", "UNKNOWN"), status_type=detail.metrics.get("overall_status", "INFO"))
                
            st.caption(f"**Unternehmensprofil:** {profile.get('company_name', 'N/A')} · {profile.get('sector', 'N/A')}")
            st.caption("Für vollständigen Deep Dive: Seite **Unternehmen** öffnen.")
