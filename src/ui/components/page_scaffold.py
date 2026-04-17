"""Konsistente Seitenkopf- und State-Komponenten für Mercator."""

from __future__ import annotations

import streamlit as st


def render_page_header(title: str, subtitle: str | None = None, actions: list[dict] | None = None) -> None:
    """Rendert den Page Header mit optionalen Aktionen rechts."""
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.title(title)
        if subtitle:
            st.caption(subtitle)
    
    if actions:
        with col2:
            st.markdown('<div style="display: flex; justify-content: flex-end; gap: 8px; align-items: center; height: 100%;">', unsafe_allow_html=True)
            cols = st.columns(len(actions))
            for i, action in enumerate(actions):
                with cols[i]:
                    if action.get("type") == "primary":
                        st.button(action["label"], key=f"header_action_{i}", on_click=action.get("on_click"), type="primary", use_container_width=True)
                    else:
                        st.button(action["label"], key=f"header_action_{i}", on_click=action.get("on_click"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)


def render_kpi_row(kpis: list[dict]) -> None:
    """Rendert eine Reihe von KPIs (max 5)."""
    cols = st.columns(len(kpis))
    for i, kpi in enumerate(kpis):
        with cols[i]:
            st.metric(
                label=kpi["label"],
                value=kpi["value"],
                delta=kpi.get("delta"),
                help=kpi.get("help")
            )


def render_loading_state() -> None:
    """Zeigt einen dezenten Ladezustand."""
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 10px; padding: 1rem; color: #6c757d;">
            <div class="stSpinner"></div>
            <span>Analysiere Daten...</span>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_empty_state(message: str) -> None:
    st.info(message)


def render_warning_state(message: str) -> None:
    st.warning(message)


def render_error_state(message: str) -> None:
    st.error(message)
