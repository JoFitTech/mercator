"""Komponente für die Context Bar (Stufe 2 des Mercator-Layouts)."""

from __future__ import annotations

from typing import Any
import streamlit as st
import pandas as pd

def render_context_bar(
    active_filters: list[str] | None = None,
    last_update: str | None = None,
    mysql_target: str | None = None,
    lookup_mode: str | None = None,
    mongo_status: bool = True,
    mysql_status: bool = True,
) -> None:
    """Rendert die Context Bar unter dem Header."""
    
    with st.container():
        cols = st.columns([0.6, 0.4])
        
        with cols[0]:
            if active_filters:
                # Rendere Filter als kleine Chips/Badges
                filter_html = " ".join([
                    f'<span style="background-color: rgba(128, 128, 128, 0.1); border: 1px solid rgba(128, 128, 128, 0.2); '
                    f'padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; margin-right: 5px; white-space: nowrap;">{f}</span>'
                    for f in active_filters
                ])
                st.markdown(f'<div style="display: flex; flex-wrap: wrap; gap: 4px; align-items: center; min-height: 32px;">'
                            f'<span style="font-size: 0.8rem; color: gray; margin-right: 8px;">Filter:</span>{filter_html}</div>', 
                            unsafe_allow_html=True)
            else:
                st.caption("Keine aktiven Filter")
        
        with cols[1]:
            # Rechtsbündige Status-Infos
            status_parts = []
            if mysql_target:
                status_parts.append(f"DB: `{mysql_target}`")
            if lookup_mode:
                status_parts.append(f"Mode: `{lookup_mode}`")
            if last_update:
                status_parts.append(f"Stand: **{last_update}**")
                
            status_text = " · ".join(status_parts)
            st.markdown(f'<div style="text-align: right; font-size: 0.8rem; color: gray;">{status_text}</div>', unsafe_allow_html=True)
            
    st.markdown("---")
