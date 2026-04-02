"""Explorer-Seite für Filterung, Tabelle und einfache Visualisierung."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.components.charts import render_bar_chart
from src.ui.components.filters import render_ticker_filter
from src.ui.components.tables import render_dataframe_table


def render_explorer_page(trades_df: pd.DataFrame) -> None:
    """Rendert interaktive Datenexploration mit Basisfiltern."""
    st.title("Datenexplorer")
    st.caption("Interaktive Filter- und Tabellenansicht für bereinigte Finanzdaten.")

    if trades_df.empty:
        st.info("Noch keine Daten im Explorer verfügbar.")
        return

    ticker_column = "ticker" if "ticker" in trades_df.columns else None
    filtered_df = trades_df

    if ticker_column:
        selected_ticker = render_ticker_filter(trades_df[ticker_column].dropna().tolist())
        if selected_ticker != "Alle":
            filtered_df = trades_df[trades_df[ticker_column] == selected_ticker]

    render_dataframe_table(filtered_df)

    if ticker_column:
        chart_df = (
            filtered_df.groupby(ticker_column)
            .size()
            .reset_index(name="anzahl_trades")
            .sort_values("anzahl_trades", ascending=False)
        )
        render_bar_chart(chart_df, x=ticker_column, y="anzahl_trades")
