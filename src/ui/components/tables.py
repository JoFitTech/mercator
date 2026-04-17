"""Tabellenkomponenten für Streamlit."""

from __future__ import annotations

from typing import Any
import pandas as pd
import streamlit as st


def render_smart_table(
    df: pd.DataFrame, 
    column_config: dict | None = None, 
    height: int = 500,
    selection_mode: str = "single-row",
    on_select: str = "ignore"
) -> Any:
    """Rendert eine Streamlit-Tabelle mit Mercator-Standardkonfiguration."""
    if df.empty:
        st.info("Keine Daten zur Anzeige verfügbar.")
        return None

    return st.dataframe(
        df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=height,
        on_select=on_select,
        selection_mode=selection_mode,
    )


def render_trade_table(df: pd.DataFrame, height: int = 600, on_select: str = "rerun") -> Any:
    """Spezialisierte Tabelle für Insider Trades mit festen Spaltenprioritäten."""
    
    # Spaltenpriorität gemäß Spec:
    # 1. Detail-Icon, 2. Symbol, 3. Insider, 4. Richtung, 5. Sector, 6. Value, 7. Score, 8. Gate, 9. Validation, 10. Date
    
    # Detail-Icon Spalte hinzufügen falls nicht vorhanden
    if "Detail" not in df.columns:
        df["Detail"] = "🔗"

    base_cols = [
        "Detail", "symbol_at_trade", "reporting_name", "direction", "sector",
        "trade_value_estimated", "score_value", "gate_status", "validation_status", "transaction_date"
    ]
    
    # Sicherstellen dass Spalten existieren
    for col in base_cols:
        if col not in df.columns:
            if col == "score_value" and "score" in df.columns:
                df["score_value"] = df["score"]
            else:
                df[col] = None
            
    col_config = {
        "Detail": st.column_config.TextColumn("Info", width="small"),
        "symbol_at_trade": st.column_config.TextColumn("Symbol", width="small", help="Ticker Symbol"),
        "reporting_name": st.column_config.TextColumn("Insider", width="medium"),
        "direction": st.column_config.TextColumn("Richtung", width="small"),
        "sector": st.column_config.TextColumn("Sector", width="medium"),
        "trade_value_estimated": st.column_config.NumberColumn("Value", format="$%.2f", width="medium"),
        "score_value": st.column_config.NumberColumn("Score", format="%.2f", width="small"),
        "gate_status": st.column_config.TextColumn("Gate", width="small"),
        "validation_status": st.column_config.TextColumn("Validation", width="small"),
        "transaction_date": st.column_config.DateColumn("Date", width="small"),
    }
    
    return render_smart_table(
        df[base_cols],
        column_config=col_config,
        height=height,
        on_select=on_select
    )
