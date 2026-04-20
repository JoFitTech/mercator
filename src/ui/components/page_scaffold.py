"""Konsistente Seitenkopf- und State-Komponenten für Mercator."""

from __future__ import annotations

import streamlit as st


def render_page_header(title: str, subtitle: str | None = None, actions: list[dict] | None = None) -> None:
    """Rendert den Page Header mit optimaler Symmetrie und Ausrichtung.
    
    Titel links, Aktionen rechts, vertikal zentriert.
    """
    col1, col2 = st.columns([0.7, 0.3], vertical_alignment="center")
    with col1:
        st.markdown(f'<h1 style="margin: 0; padding: 0; line-height: 1.2;">{title}</h1>', unsafe_allow_html=True)
        if subtitle:
            st.caption(subtitle)
    
    results = []
    if actions:
        with col2:
            # Wir nutzen eine Spalten-Logik innerhalb der Aktionsspalte für saubere Button-Anordnung
            n_actions = len(actions)
            action_cols = st.columns(n_actions)
            for i, action in enumerate(actions):
                with action_cols[i]:
                    btn_type = action.get("type", "secondary")
                    res = st.button(
                        action["label"], 
                        key=f"header_action_{title}_{i}", 
                        on_click=action.get("on_click"), 
                        type=btn_type, 
                        use_container_width=True
                    )
                    results.append(res)
    return results


def render_kpi_row(kpis: list[dict]) -> None:
    """Rendert eine Reihe von KPIs in konsistenten Karten.

    Optional kann pro KPI ein ``subtext`` übergeben werden.
    """
    if not kpis:
        return

    n = len(kpis)
    cols = st.columns(n)
    for i, kpi in enumerate(kpis):
        with cols[i]:
            st.metric(
                label=kpi["label"],
                value=kpi["value"],
                delta=kpi.get("delta"),
                help=kpi.get("help")
            )
            subtext = kpi.get("subtext")
            if subtext:
                st.caption(subtext)


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
