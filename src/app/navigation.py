"""Navigations-Logik für Mercator (Requirement 5.1)."""

from __future__ import annotations
import streamlit as st
from typing import Literal

# Typer-Definition für Seiten
PageName = Literal["Dashboard", "Trades", "Unternehmen", "Admin", "Einstellungen", "Methodik", "Trade-Detail", "Unternehmens-Detail"]

def render_navigation_sidebar():
    """Rendert die Hauptnavigation in der Sidebar."""
    st.sidebar.title("Navigation")
    
    # Bestimme aktuelle Seite aus Session State oder Default
    if "nav_target" not in st.session_state:
        st.session_state["nav_target"] = "Dashboard"
        
    nav_options = {
        "Dashboard": "Dashboard",
        "Trade-Explorer": "Trades",
        "Unternehmen": "Unternehmen",
        "Einstellungen": "Einstellungen",
        "Methodik": "Methodik",
        "Admin": "Admin",
    }
    
    # Finde Index der aktuellen Seite für das Radio-Menü
    current_label = next((k for k, v in nav_options.items() if v == st.session_state["nav_target"]), "Dashboard")
    options_list = list(nav_options.keys())
    
    selected_label = st.sidebar.radio(
        "Hauptmenü",
        options=options_list,
        index=options_list.index(current_label) if current_label in options_list else 0
    )
    
    # Update nav_target bei Klick (wenn es nicht durch Deep-Link überschrieben wurde)
    new_target = nav_options[selected_label]
    if st.session_state["nav_target"] not in ["Trade-Detail", "Unternehmens-Detail"]:
         st.session_state["nav_target"] = new_target
    
    # Zurück-Button für Detailseiten
    if st.session_state["nav_target"] in ["Trade-Detail", "Unternehmens-Detail"]:
        st.sidebar.markdown("---")
        if st.sidebar.button("Zurück zur Liste"):
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
