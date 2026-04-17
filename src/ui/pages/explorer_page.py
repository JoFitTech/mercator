"""Explorer-Seite mit interaktiven Filtern auf bereinigte Trades."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.services.analysis_service import AnalysisService
from src.services.app_settings_service import AppSettingsService
from src.ui.components.context_bar import render_context_bar
from src.ui.components.page_scaffold import render_empty_state, render_page_header


PRIMARY_DIRECTIONS = ["Alle", "BUY", "SELL"]
TR_UNIVERSE_OPTIONS = ["Alle", "Im Universum", "Nicht im Universum", "Unbekannt"]


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
        "trade_republic": "Alle",
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
    if filters.get("trade_republic") != "Alle":
        parts.append(f"Trade Republic: **{filters['trade_republic']}**")

    st.caption("Aktive Filter: " + (" · ".join(parts) if parts else "Keine (Standardansicht)"))


from src.ui.components.page_scaffold import render_empty_state, render_kpi_row, render_page_header
from src.ui.components.tables import render_trade_table
from src.ui.components.status_badges import score_class_badge, status_badge

def render_explorer_page(service: AnalysisService, settings_service: AppSettingsService | None = None) -> None:
    """Rendert die Trades-Seite als operative Hauptarbeitsfläche."""
    
    render_page_header(
        "Trades", 
        "Fokussierter Screener für Trade-Relevanz, Richtung und Scoring.",
        actions=[{"label": "Export CSV", "type": "secondary"}]
    )

    # 1. Scope Selection (Context Bar)
    scope = render_context_bar(with_scope=True, scope_options={})
    
    # Mapping
    api_direction = None
    if scope.get("direction") == "BUY":
        api_direction = "A"
    elif scope.get("direction") == "SELL":
        api_direction = "D"

    # Daten laden
    with st.spinner("Lade Trades..."):
        data = service.get_filtered_trades(
            filters={"acquisition_or_disposition": api_direction},
            limit=1000,
            accumulate=scope.get("accumulate", True),
            min_value=0,
        )

    if data.empty:
        render_empty_state("Keine Treffer für den aktuellen Scope.")
        return

    # 2. KPI Row
    kpi_data = [
        {"label": "Treffer", "value": f"{len(data):,}"},
        {"label": "BUY", "value": f"{int((data.get('direction', pd.Series(dtype='object')) == 'BUY').sum()):,}"},
        {"label": "Gate PASS", "value": f"{int((data.get('gate_status', pd.Series(dtype='object')).astype(str).str.upper() == 'PASS').sum()):,}"},
    ]
    
    avg_score = pd.to_numeric(data.get('score'), errors='coerce').mean()
    kpi_data.append({"label": "Ø Score", "value": f"{avg_score:.2f}" if not pd.isna(avg_score) else "-"})
    
    render_kpi_row(kpi_data)

    st.markdown("---")

    # 3. Primary Work Area (Table & Detail Drawer)
    main_col, drawer_col = st.columns([0.7, 0.3])
    
    with main_col:
        st.subheader("Trade-Arbeitsfläche")
        event = render_trade_table(data, height=600)
    
    with drawer_col:
        st.subheader("Aktionen")
        if event and event.get("selection") and event["selection"].get("rows"):
            selected_row_idx = event["selection"]["rows"][0]
            selected_trade = data.iloc[selected_row_idx]
            
            with st.container(border=True):
                st.markdown(f"### {selected_trade.get('symbol_at_trade', 'N/A')}")
                st.write(f"**Insider:** {selected_trade.get('reporting_name', 'N/A')}")
                st.write(f"**Richtung:** {selected_trade.get('direction', 'N/A')}")
                st.write(f"**Wert:** ${selected_trade.get('trade_value_estimated', 0):,.0f}")
                
                st.markdown("---")
                if st.button("🔍 Trade Detail öffnen", type="primary", use_container_width=True):
                    st.session_state["selected_trade_key"] = selected_trade.get('dedupe_key')
                    st.rerun()
                
                if st.button("🏢 Unternehmens-Deep-Dive", use_container_width=True):
                    st.session_state["selected_company_symbol"] = selected_trade.get('symbol_at_trade')
                    st.rerun()
        else:
            st.info("Wählen Sie einen Trade aus der Tabelle aus.")
