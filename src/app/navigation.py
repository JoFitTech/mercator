"""Navigations-Logik für Mercator (Requirement 5.1)."""

from __future__ import annotations
import streamlit as st
from typing import Literal

# Typer-Definition für Seiten
PageName = Literal["Dashboard", "Trades", "Unternehmen", "Admin", "Einstellungen", "Methodik", "Trade-Detail", "Unternehmens-Detail"]

NAV_OPTIONS: dict[str, str] = {
    "Dashboard": "Dashboard",
    "Trade-Explorer": "Trades",
    "Unternehmen": "Unternehmen",
    "Einstellungen": "Einstellungen",
    "Methodik": "Methodik",
    "Admin": "Admin",
}

DETAIL_PAGES = {"Trade-Detail", "Unternehmens-Detail"}

def render_navigation_topbar() -> PageName:
    """Rendert die Hauptnavigation als obere Navbar."""

    # Bestimme aktuelle Seite aus Session State oder Default.
    if "nav_target" not in st.session_state:
        st.session_state["nav_target"] = "Dashboard"

    current_label = next(
        (k for k, v in NAV_OPTIONS.items() if v == st.session_state["nav_target"]),
        "Dashboard",
    )
    options_list = list(NAV_OPTIONS.keys())

    selected_label = st.radio(
        "Navigation",
        options=options_list,
        index=options_list.index(current_label) if current_label in options_list else 0,
        horizontal=True,
        label_visibility="collapsed",
    )

    # Update nav_target nur außerhalb von Detailseiten, damit Deep-Link-Details stabil bleiben.
    new_target = NAV_OPTIONS[selected_label]
    if st.session_state["nav_target"] not in DETAIL_PAGES:
        st.session_state["nav_target"] = new_target

    # Zurück-Button für Detailseiten.
    if st.session_state["nav_target"] in DETAIL_PAGES:
        if st.button("Zurück zur Liste", key="top_nav_back_to_list"):
            if st.session_state["nav_target"] == "Trade-Detail":
                st.session_state["nav_target"] = "Trades"
            else:
                st.session_state["nav_target"] = "Unternehmen"
            st.rerun()

    return st.session_state["nav_target"]

def render_system_status_sidebar(db_status, mysql_res, advanced_mode=False):
    """Rendert den System-Status in der Sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("System-Status")
    
    # MySQL Status
    mysql_color = "green" if db_status.mysql.is_connected else "red"
    mysql_label = "MySQL: Online" if db_status.mysql.is_connected else "MySQL: Offline"
    st.sidebar.markdown(f":{mysql_color}[{mysql_label}]")
    if mysql_res and mysql_res.active_target:
        st.sidebar.caption(f"Target: {mysql_res.active_target}")
        
    # MongoDB Status
    mongo_color = "green" if db_status.mongo.is_connected else "red"
    mongo_label = "MongoDB: Online" if db_status.mongo.is_connected else "MongoDB: Offline"
    st.sidebar.markdown(f":{mongo_color}[{mongo_label}]")

    mode_label = "Betriebsmodus: Schreiben aktiv" if db_status.is_write_mode_available else "Betriebsmodus: Lesemodus"
    st.sidebar.caption(mode_label)
    if not db_status.is_settings_persistence_available:
        st.sidebar.caption("Einstellungen: nur Sitzung")
    
    # Advanced Mode Toggle
    if advanced_mode:
        st.sidebar.info("Expertenmodus aktiv")
