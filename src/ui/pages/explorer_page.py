"""Explorer-Seite mit interaktiven Filtern auf bereinigte Trades."""

from __future__ import annotations

import streamlit as st
import pandas as pd
from typing import Any

from src.services.analysis_service import AnalysisService
from src.services.app_settings_service import AppSettingsService


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


def render_explorer_page(service: AnalysisService, settings_service: AppSettingsService | None = None) -> None:
    """Rendert Filter und kompakte Screener-Tabelle für Insider-Trades."""
    st.title("Mercator")
    st.markdown("### Insider Trades Screener")

    default_filters = {
        "symbol": "",
        "reporting_name": "",
        "direction": "Alle",
        "min_value": 0,
        "accumulate": True,
        "show_raw": False,
    }

    if "explorer_filters" not in st.session_state:
        if settings_service is not None:
            persisted = settings_service.load_filter("explorer", "filters", default_filters)
            st.session_state.explorer_filters = persisted if isinstance(persisted, dict) else default_filters.copy()
        else:
            st.session_state.explorer_filters = default_filters.copy()

    # Filterleiste
    with st.expander("Filter & Optionen", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        persisted_direction = str(st.session_state.explorer_filters.get("direction", "Alle"))
        symbol = c1.text_input("Ticker", value=str(st.session_state.explorer_filters.get("symbol", "")), placeholder="z.B. AAPL")
        reporting = c2.text_input("Insider", value=str(st.session_state.explorer_filters.get("reporting_name", "")), placeholder="Name...")
        direction = c3.selectbox(
            "Richtung",
            ["Alle", "BUY", "SELL"],
            index=["Alle", "BUY", "SELL"].index(persisted_direction if persisted_direction in {"Alle", "BUY", "SELL"} else "Alle"),
        )
        min_value = c4.number_input("Min. Wert ($)", value=int(st.session_state.explorer_filters.get("min_value", 0)), step=10000)

        c5, c6 = st.columns(2)
        accumulate = c5.toggle("Trades akkumulieren", value=bool(st.session_state.explorer_filters.get("accumulate", True)))
        show_raw = c6.toggle("Rohdaten zeigen", value=bool(st.session_state.explorer_filters.get("show_raw", False)))

        # State aktualisieren
        st.session_state.explorer_filters.update(
            {
                "symbol": symbol.strip().upper(),
                "reporting_name": reporting.strip(),
                "direction": direction,
                "min_value": min_value,
                "accumulate": accumulate,
                "show_raw": show_raw,
            }
        )

        if settings_service is not None:
            settings_service.save_filter("explorer", "filters", st.session_state.explorer_filters)

    # Daten laden
    api_direction = None
    if direction == "BUY":
        api_direction = "A"
    elif direction == "SELL":
        api_direction = "D"

    filters = {
        "symbol": symbol.strip().upper() or None,
        "reporting_name": reporting.strip() or None,
        "acquisition_or_disposition": api_direction,
    }

    data = service.get_filtered_trades(
        filters=filters,
        limit=1000,
        accumulate=accumulate and not show_raw,
        min_value=float(min_value),
    )

    if data.empty:
        st.info("Keine Daten gefunden, die den Filtern entsprechen.")
        return

    st.subheader(f"{len(data)} Ergebnisse")

    if accumulate and not show_raw:
        display_df = data[
            [
                "transaction_date",
                "symbol_at_trade",
                "company_name",
                "reporting_name",
                "direction",
                "accumulated_qty",
                "accumulated_avg_price_weighted",
                "accumulated_trade_value_estimated",
                "score",
                "score_class",
                "gate_status",
                "validation_status",
                "is_accumulated",
                "accumulated_trade_count",
            ]
        ].copy()

        display_df["Type"] = display_df.apply(
            lambda r: f"ACC x{r['accumulated_trade_count']}" if r["is_accumulated"] else "Single", axis=1
        )

        final_cols = [
            "transaction_date",
            "symbol_at_trade",
            "company_name",
            "reporting_name",
            "direction",
            "accumulated_qty",
            "accumulated_avg_price_weighted",
            "accumulated_trade_value_estimated",
            "score",
            "score_class",
            "gate_status",
            "validation_status",
            "Type",
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
            "score": st.column_config.NumberColumn("Score", format="%.2f"),
            "score_class": st.column_config.TextColumn("Score Klasse"),
            "gate_status": st.column_config.TextColumn("Gate"),
            "validation_status": st.column_config.TextColumn("Validation"),
            "Type": st.column_config.TextColumn("Typ"),
        }
    else:
        display_df = data[
            [
                "transaction_date",
                "symbol_at_trade",
                "company_name",
                "reporting_name",
                "direction",
                "qty",
                "price",
                "trade_value_estimated",
                "score",
                "score_class",
                "gate_status",
                "validation_status",
            ]
        ].copy()

        final_cols = [
            "transaction_date",
            "symbol_at_trade",
            "company_name",
            "reporting_name",
            "direction",
            "qty",
            "price",
            "trade_value_estimated",
            "score",
            "score_class",
            "gate_status",
            "validation_status",
        ]

        col_config = {
            "transaction_date": st.column_config.DateColumn("Datum"),
            "symbol_at_trade": st.column_config.TextColumn("Ticker"),
            "company_name": st.column_config.TextColumn("Firma"),
            "reporting_name": st.column_config.TextColumn("Insider"),
            "direction": st.column_config.TextColumn("Richtung"),
            "qty": st.column_config.NumberColumn("Stückzahl", format="%d"),
            "price": st.column_config.NumberColumn("Preis", format="$%.2f"),
            "trade_value_estimated": st.column_config.NumberColumn("Wert ($)", format="$%.2f"),
            "score": st.column_config.NumberColumn("Score", format="%.2f"),
            "score_class": st.column_config.TextColumn("Score Klasse"),
            "gate_status": st.column_config.TextColumn("Gate"),
            "validation_status": st.column_config.TextColumn("Validation"),
        }

    st.dataframe(
        display_df[final_cols],
        column_config=col_config,
        use_container_width=True,
        hide_index=True,
    )

    st.info("Klicken Sie auf 'Ticker-Detailansicht' in der Sidebar für tiefergehende Analysen eines einzelnen Wertpapiers.")
