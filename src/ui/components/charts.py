"""Chart-Helfer für die Streamlit-Oberfläche."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from src.ui.ui_theme import CHART_PALETTE


def render_bar_chart(df: pd.DataFrame, x: str, y: str) -> None:
    """Zeigt ein einfaches Balkendiagramm, falls Daten vorhanden sind."""
    if df.empty or x not in df.columns or y not in df.columns:
        st.info("Für das Diagramm sind aktuell keine geeigneten Daten vorhanden.")
        return

    st.bar_chart(df.set_index(x)[y])


def render_horizontal_bar_chart(
    df: pd.DataFrame,
    category_col: str,
    value_col: str,
    title: str,
    caption: str | None = None,
) -> None:
    """Rendert ein horizontales Balkendiagramm mit zentraler Farbpalette."""
    if title:
        st.markdown(f"#### {title}")
    if caption:
        st.caption(caption)

    if df.empty or category_col not in df.columns or value_col not in df.columns:
        st.info("Fuer dieses Diagramm sind aktuell keine Daten verfuegbar.")
        return

    chart_df = df[[category_col, value_col]].copy()
    chart_df[category_col] = chart_df[category_col].fillna("Unbekannt").astype(str)
    chart_df[value_col] = pd.to_numeric(chart_df[value_col], errors="coerce").fillna(0)
    chart_df = chart_df.sort_values(value_col, ascending=False).head(12)

    st.vega_lite_chart(
        chart_df,
        {
            "mark": {"type": "bar", "cornerRadiusEnd": 2},
            "encoding": {
                "y": {
                    "field": category_col,
                    "type": "nominal",
                    "sort": "-x",
                    "title": "Kategorie",
                },
                "x": {
                    "field": value_col,
                    "type": "quantitative",
                    "title": "Anzahl",
                },
                "color": {
                    "field": category_col,
                    "type": "nominal",
                    "legend": None,
                    "scale": {"range": CHART_PALETTE["categorical"]},
                },
                "tooltip": [
                    {"field": category_col, "type": "nominal", "title": "Kategorie"},
                    {"field": value_col, "type": "quantitative", "title": "Wert"},
                ],
            },
            "view": {"stroke": None},
        },
        use_container_width=True,
    )


