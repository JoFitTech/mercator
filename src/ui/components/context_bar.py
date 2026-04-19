"""Komponente für die Context Bar (Stufe 2 des Mercator-Layouts)."""

from __future__ import annotations

from typing import Any
import streamlit as st
import pandas as pd

def render_scope_bar(
    period_options: list[str] | None = None,
    key_prefix: str = ""
) -> dict[str, Any]:
    """Rendert eine spezialisierte Bar für Scope-Filter (Zeitraum, Akkumulation, Richtung)."""
    if period_options is None:
        period_options = ["Last 30D", "Last 90D", "YTD", "All Time"]
        
    container = st.container(border=True)
    with container:
        c1, c2, c3, c4, c5 = st.columns([0.2, 0.2, 0.2, 0.2, 0.2])
        
        with c1:
            period = st.selectbox("Zeitraum", options=period_options, key=f"{key_prefix}scope_period")
        with c2:
            accumulate = st.toggle("Akkumulieren", value=True, key=f"{key_prefix}scope_accumulate")
        with c3:
            direction = st.selectbox("Richtung", options=["Alle", "BUY", "SELL"], key=f"{key_prefix}scope_direction")
        with c4:
            st.write("")
        with c5:
            if st.button("Reset Filters", key=f"{key_prefix}reset_btn", use_container_width=True):
                for key in [f"{key_prefix}scope_period", f"{key_prefix}scope_accumulate", f"{key_prefix}scope_direction", "selected_ticker"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        return {
            "period": period,
            "accumulate": accumulate,
            "direction": direction
        }

def render_filter_chip_bar(active_filters: dict[str, Any] | None = None) -> None:
    """Rendert aktive Filter als Chips."""
    if not active_filters:
        st.caption("🌍 Gesamter Markt")
        return

    display_chips = []
    if isinstance(active_filters, dict):
        filter_items = active_filters.items()
    elif isinstance(active_filters, list):
        filter_items = [(None, v) for v in active_filters]
    else:
        filter_items = []

    for k, v in filter_items:
        if v and v not in ("All", "Alle", "All Time"):
            if isinstance(v, (list, tuple)) and len(v) == 2:
                display_chips.append(f"{k + ': ' if k else ''}{v[0]} - {v[1]}")
            else:
                display_chips.append(f"{k + ': ' if k else ''}{v}")
    
    if display_chips:
        chips_html = "".join([
            f'<span class="mercator-badge" style="background-color: #f1f3f5; color: #1c7ed6; border: 1px solid #d0ebff; padding: 4px 10px; margin-right: 8px; border-radius: 16px; font-size: 0.75rem;">{f}</span>'
            for f in display_chips
        ])
        st.markdown(f'<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 4px; margin-bottom: 1rem;">{chips_html}</div>', unsafe_allow_html=True)
    else:
        st.caption("🌍 Gesamter Markt (keine Filter aktiv)")

def render_status_bar(last_update: str | None = None, mysql_target: str | None = None) -> None:
    """Rendert eine Status-Bar mit Last Update Info."""
    if last_update:
        st.markdown(f'<div style="text-align: right; font-size: 0.8rem; color: #adb5bd; margin-bottom: 1rem;">Stand: <span class="mono" style="color: #495057; font-weight: 500;">{last_update}</span> ({mysql_target or "local"})</div>', unsafe_allow_html=True)
