"""Explorer-Seite mit interaktiven Filtern auf bereinigte Trades."""

from __future__ import annotations

import streamlit as st
import pandas as pd
from typing import Any

from src.services.analysis_service import AnalysisService
from src.ui.pages.ticker_detail_page import format_number


def format_currency_compact(value: Any) -> str:
    """Formatiert Währungswerte kompakt (z.B. 1.25M, 842k)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    val = float(value)
    if abs(val) >= 1_000_000:
        return f"{val / 1_000_000:.2f}M"
    if abs(val) >= 1_000:
        return f"{val / 1_000:.1f}k"
    return f"{val:.2f}"


def render_explorer_page(service: AnalysisService) -> None:
    """Rendert Filter und kompakte Screener-Tabelle für Insider-Trades."""
    st.title("Mercator")
    st.markdown("### Insider Trades Screener")
    
    # Session State für Filter
    if "explorer_filters" not in st.session_state:
        st.session_state.explorer_filters = {
            "symbol": "",
            "reporting_name": "",
            "direction": "Alle",
            "min_value": 0,
            "accumulate": True,
            "show_raw": False
        }

    # Filterleiste
    with st.expander("Filter & Optionen", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        symbol = c1.text_input("Ticker", value=st.session_state.explorer_filters["symbol"], placeholder="z.B. AAPL")
        reporting = c2.text_input("Insider", value=st.session_state.explorer_filters["reporting_name"], placeholder="Name...")
        direction = c3.selectbox("Richtung", ["Alle", "BUY", "SELL"], 
                               index=["Alle", "BUY", "SELL"].index(st.session_state.explorer_filters["direction"]))
        min_value = c4.number_input("Min. Wert ($)", value=st.session_state.explorer_filters["min_value"], step=10000)

        c5, c6, c7 = st.columns(3)
        accumulate = c5.toggle("Trades akkumulieren", value=st.session_state.explorer_filters["accumulate"])
        show_raw = c6.toggle("Rohdaten zeigen", value=st.session_state.explorer_filters["show_raw"])
        
        # State aktualisieren
        st.session_state.explorer_filters.update({
            "symbol": symbol.strip().upper(),
            "reporting_name": reporting.strip(),
            "direction": direction,
            "min_value": min_value,
            "accumulate": accumulate,
            "show_raw": show_raw
        })

    # Daten laden
    api_direction = None
    if direction == "BUY": api_direction = "A"
    elif direction == "SELL": api_direction = "D"

    filters = {
        "symbol": symbol.strip().upper() or None,
        "reporting_name": reporting.strip() or None,
        "acquisition_or_disposition": api_direction,
    }
    
    # AnalysisService aufrufen
    data = service.get_filtered_trades(
        filters=filters, 
        limit=1000, 
        accumulate=accumulate and not show_raw,
        min_value=float(min_value)
    )
    
    if data.empty:
        st.info("Keine Daten gefunden, die den Filtern entsprechen.")
        return

    st.subheader(f"{len(data)} Ergebnisse")

    # Styling & Spaltenlogik
    # Pflichtspalten laut Anforderung
    if accumulate and not show_raw:
        # Wir behalten die numerischen Spalten für korrektes Sorting im st.dataframe
        display_df = data[[
            "transaction_date", "symbol_at_trade", "company_name", "reporting_name",
            "direction", "accumulated_qty", "accumulated_avg_price_weighted", 
            "accumulated_trade_value_estimated", "is_accumulated", "accumulated_trade_count"
        ]].copy()
        
        display_df["Type"] = display_df.apply(
            lambda r: f"ACC x{r['accumulated_trade_count']}" if r['is_accumulated'] else "Single", axis=1
        )
        
        final_cols = [
            "transaction_date", "symbol_at_trade", "company_name", "reporting_name", 
            "direction", "accumulated_qty", "accumulated_avg_price_weighted", 
            "accumulated_trade_value_estimated", "Type"
        ]
        
        col_config = {
            "transaction_date": st.column_config.DateColumn("Datum"),
            "symbol_at_trade": st.column_config.TextColumn("Ticker"),
            "company_name": st.column_config.TextColumn("Firma"),
            "reporting_name": st.column_config.TextColumn("Insider"),
            "direction": st.column_config.TextColumn("Richtung"),
            "accumulated_qty": st.column_config.NumberColumn("Stückzahl", format="%d"),
            "accumulated_avg_price_weighted": st.column_config.NumberColumn("Preis", format="$%.2f"),
            "accumulated_trade_value_estimated": st.column_config.NumberColumn("Wert ($)", format="$%.2f"),
            "Type": st.column_config.TextColumn("Typ")
        }
    else:
        display_df = data[[
            "transaction_date", "symbol_at_trade", "company_name", "reporting_name",
            "direction", "qty", "price", "trade_value_estimated"
        ]].copy()
        
        final_cols = [
            "transaction_date", "symbol_at_trade", "company_name", "reporting_name", 
            "direction", "qty", "price", "trade_value_estimated"
        ]
        
        col_config = {
            "transaction_date": st.column_config.DateColumn("Datum"),
            "symbol_at_trade": st.column_config.TextColumn("Ticker"),
            "company_name": st.column_config.TextColumn("Firma"),
            "reporting_name": st.column_config.TextColumn("Insider"),
            "direction": st.column_config.TextColumn("Richtung"),
            "qty": st.column_config.NumberColumn("Stückzahl", format="%d"),
            "price": st.column_config.NumberColumn("Preis", format="$%.2f"),
            "trade_value_estimated": st.column_config.NumberColumn("Wert ($)", format="$%.2f")
        }

    # Anzeige als Tabelle
    st.dataframe(
        display_df[final_cols],
        column_config=col_config,
        use_container_width=True,
        hide_index=True
    )
    
    st.info("Klicken Sie auf 'Ticker-Detailansicht' in der Sidebar für tiefergehende Analysen eines einzelnen Wertpapiers.")
