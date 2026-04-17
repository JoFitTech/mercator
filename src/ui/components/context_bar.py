"""Komponente für die Context Bar (Stufe 2 des Mercator-Layouts)."""

from __future__ import annotations

from typing import Any
import streamlit as st
import pandas as pd

def render_context_bar(
    active_filters: list[str] | None = None,
    last_update: str | None = None,
    mysql_target: str | None = None,
    with_scope: bool = False,
    scope_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rendert die Context Bar (Scope Area)."""
    
    container = st.container(border=True)
    with container:
        if with_scope and scope_options:
            c1, c2, c3, c4, c5 = st.columns([0.2, 0.2, 0.2, 0.2, 0.2])
            
            with c1:
                period = st.selectbox("Zeitraum", options=["Last 30D", "Last 90D", "YTD", "All Time"], key="scope_period")
            with c2:
                accumulate = st.toggle("Akkumulieren", value=True, key="scope_accumulate")
            with c3:
                direction = st.selectbox("Richtung", options=["Alle", "BUY", "SELL"], key="scope_direction")
            with c4:
                # Placeholder für weitere Filter
                st.write("")
            with c5:
                if st.button("Reset Filters", use_container_width=True):
                    st.session_state.clear()
                    st.rerun()
            
            return {
                "period": period,
                "accumulate": accumulate,
                "direction": direction
            }

        # Fallback / Simple Mode
        cols = st.columns([0.7, 0.3])
        with cols[0]:
            if active_filters:
                chips_html = "".join([
                    f'<span class="mercator-badge" style="background-color: #e9ecef; color: #495057; margin-right: 6px;">{f}</span>'
                    for f in active_filters
                ])
                st.markdown(f'<div style="display: flex; align-items: center; min-height: 32px;">{chips_html}</div>', unsafe_allow_html=True)
            else:
                st.caption("Kein Scope-Filter aktiv")
        
        with cols[1]:
            if last_update:
                st.markdown(f'<div style="text-align: right; font-size: 0.8rem; color: #6c757d;">Stand: <span class="mono">{last_update}</span></div>', unsafe_allow_html=True)

    return {}
