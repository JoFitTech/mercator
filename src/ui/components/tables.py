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
    """Spezialisierte Tabelle für Insider Trades mit optimierten Spaltenbreiten (kein horizontales Scrollen).

    Kritisch für Web-Test-Readiness:
    - `score` wird konsistent aus dem Repository als `score` geliefert
    - `direction` wird aus `acquisition_or_disposition` berechnet (A=BUY, D=SELL)
    """

    # Spaltenpriorität gemäß Spec:
    # 1. Symbol, 2. Insider, 3. Richtung, 4. Value, 5. Score, 6. Date
    
    # Defensive Kopie, damit Seitenzustände nicht durch Nebenwirkungen mutiert werden.
    df = df.copy().reset_index(drop=True)

    # Richtung normalisieren (falls nicht vorhanden)
    if "direction" not in df.columns and "acquisition_or_disposition" in df.columns:
        df["direction"] = df["acquisition_or_disposition"].map({"A": "BUY", "D": "SELL"}).fillna("UNKNOWN")
    if "direction" not in df.columns:
        df["direction"] = "UNKNOWN"

    # Alle potenziellen Spalten für die Datenbasis
    all_cols = [
        "symbol_at_trade", "reporting_name", "direction", "sector",
        "trade_value_estimated", "score", "gate_status", "validation_status", "transaction_date"
    ]
    
    # Sicherstellen dass Spalten existieren
    for col in all_cols:
        if col not in df.columns:
            df[col] = None

    # Sichtbare Spalten drastisch einschränken um horizontales Scrollen zu vermeiden
    # Wir zeigen nur die absolut kritischen Spalten.
    visible_cols = ["symbol_at_trade", "reporting_name", "direction", "trade_value_estimated", "score", "transaction_date"]

    col_config = {
        "symbol_at_trade": st.column_config.TextColumn("Symbol", width="small", pinned=True),
        "reporting_name": st.column_config.TextColumn("Insider", width="medium"),
        "direction": st.column_config.TextColumn("Richtung", width="small"),
        "sector": st.column_config.TextColumn("Sektor", width="medium"),
        "trade_value_estimated": st.column_config.NumberColumn("Wert", format="$%d", width="small"),
        "score": st.column_config.NumberColumn("Score", format="%.1f", width="small"),
        "gate_status": st.column_config.TextColumn("Gate-Status", width="small"),
        "validation_status": st.column_config.TextColumn("Validierungsstatus", width="small"),
        "transaction_date": st.column_config.DateColumn("Datum", width="small", format="DD.MM.YY"),
    }
    
    return st.dataframe(
        df[all_cols],
        column_order=visible_cols,
        column_config=col_config,
        use_container_width=True,
        hide_index=True,
        height=height,
        on_select=on_select,
        selection_mode="single-row",
    )
