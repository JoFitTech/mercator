"""Tabellenkomponenten für Streamlit."""

from __future__ import annotations

from typing import Any
import pandas as pd
import streamlit as st


def _is_missing_value(value: object) -> bool:
    if value is None:
        return True
    if pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "none", "n/a"}


def _safe_text(value: object, fallback: str) -> str:
    return fallback if _is_missing_value(value) else str(value).strip()


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

    visible_cols = [
        "transaction_date", "symbol_at_trade", "reporting_name", "direction",
        "trade_value", "accumulated_trade_count", "transaction_code_class", "gate_status", "filing_age_days",
        "market_cap", "industry", "score", "score_class", "decision_status",
        "technical_state", "liquidity_state", "validation_status",
    ]

    # Sicherstellen dass sichtbare Spalten existieren
    for col in visible_cols:
        if col not in df.columns:
            df[col] = None

    df["symbol_at_trade"] = df["symbol_at_trade"].apply(lambda value: _safe_text(value, "–"))
    df["reporting_name"] = df["reporting_name"].apply(lambda value: _safe_text(value, "Unbekannter Insider"))
    df["trade_value"] = pd.to_numeric(df.get("trade_value", df.get("trade_value_estimated")), errors="coerce")
    if "accumulated_trade_value_estimated" in df.columns:
        accum_val = pd.to_numeric(df["accumulated_trade_value_estimated"], errors="coerce")
        df["trade_value"] = df["trade_value"].fillna(accum_val)
    if "accumulated_trade_count" in df.columns:
        df["accumulated_trade_count"] = pd.to_numeric(df["accumulated_trade_count"], errors="coerce")
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df["gate_status"] = df["gate_status"].apply(lambda value: _safe_text(value, "Nicht verfügbar"))
    df["validation_status"] = df["validation_status"].apply(lambda value: _safe_text(value, "Nicht verfügbar"))
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")

    col_config = {
        "symbol_at_trade": st.column_config.TextColumn("Symbol", width="small", pinned=True),
        "reporting_name": st.column_config.TextColumn("Insider", width="medium"),
        "direction": st.column_config.TextColumn("Richtung", width="small"),
        "sector": st.column_config.TextColumn("Sektor", width="medium"),
        "trade_value": st.column_config.NumberColumn("Trade Value", format="$%.0f", width="small"),
        "accumulated_trade_count": st.column_config.NumberColumn("#Trades", format="%d", width="small"),
        "transaction_code_class": st.column_config.TextColumn("Tx Code Class", width="small"),
        "core_insider_score": st.column_config.NumberColumn("Core Insider", format="%.1f", width="small"),
        "final_score": st.column_config.NumberColumn("Final Score", format="%.1f", width="small"),
        "final_class": st.column_config.TextColumn("Class", width="small"),
        "decision_status": st.column_config.TextColumn("Decision", width="small"),
        "tr_availability_state": st.column_config.TextColumn("TR Status", width="small"),
        "primary_exchange": st.column_config.TextColumn("Listing", width="small"),
        "filing_age_days": st.column_config.NumberColumn("Filing Age", width="small"),
        "earnings_distance_days": st.column_config.NumberColumn("Earnings Dist.", width="small"),
        "score": st.column_config.NumberColumn("Score", format="%.1f", width="small"),
        "gate_status": st.column_config.TextColumn("Gate-Status", width="small"),
        "validation_status": st.column_config.TextColumn("Validierungsstatus", width="small"),
        "transaction_date": st.column_config.DateColumn("Datum", width="small", format="DD.MM.YY"),
    }

    return st.dataframe(
        df[visible_cols],
        column_order=visible_cols,
        column_config=col_config,
        use_container_width=True,
        hide_index=True,
        height=height,
        on_select=on_select,
        selection_mode="single-row",
    )


def get_single_selected_row_index(event: dict[str, Any] | None, row_count: int) -> int | None:
    """Liest robust den ausgewählten Zeilenindex aus einem Streamlit-Selection-Event."""
    if not event:
        return None
    selected = event.get("selection", {}).get("rows", [])
    if not selected:
        return None
    try:
        idx = int(selected[0])
    except (TypeError, ValueError, IndexError):
        return None
    if idx < 0 or idx >= row_count:
        return None
    return idx


def sort_dashboard_top_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Sorgt für eine stabile, nachvollziehbare Default-Sortierung im Dashboard."""
    work = df.copy()
    if "accumulated_trade_value_estimated" in work.columns:
        work["accumulated_trade_value_estimated"] = pd.to_numeric(
            work["accumulated_trade_value_estimated"], errors="coerce"
        )
    if "trade_date" in work.columns:
        work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce")
    sort_cols = [c for c in ["accumulated_trade_value_estimated", "trade_date"] if c in work.columns]
    if sort_cols:
        work = work.sort_values(
            sort_cols,
            ascending=[False] * len(sort_cols),
            na_position="last",
        )
    return work.reset_index(drop=True)


def render_dashboard_top_table(df: pd.DataFrame, key: str, height: int = 260) -> Any:
    """Kompakte Top-Tabellen mit Row-Selection für das Dashboard."""
    if df.empty:
        st.info("Keine Einträge im gewählten Zeitraum.")
        return None

    work = sort_dashboard_top_rows(df)
    if "trade_date" not in work.columns:
        work["trade_date"] = None

    col_config = {
        "symbol_at_trade": st.column_config.TextColumn("Symbol", width="small"),
        "reporting_name": st.column_config.TextColumn("Reporting Name", width="medium"),
        "accumulated_trade_value_estimated": st.column_config.NumberColumn("Trade Value", format="$%d", width="small"),
        "trade_date": st.column_config.DateColumn("Datum", format="DD.MM.YYYY", width="small"),
        "profile_status": st.column_config.TextColumn("Profil", width="small"),
    }

    visible_cols = ["symbol_at_trade", "reporting_name", "accumulated_trade_value_estimated", "trade_date", "profile_status"]
    for col in visible_cols:
        if col not in work.columns:
            work[col] = None

    return st.dataframe(
        work,
        key=key,
        column_order=visible_cols,
        column_config=col_config,
        use_container_width=True,
        hide_index=True,
        height=height,
        on_select="rerun",
        selection_mode="single-row",
    )
