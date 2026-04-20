"""Navigations-Logik für Mercator (Requirement 5.1)."""

from __future__ import annotations
from typing import Literal

import streamlit as st

# Typer-Definition für Seiten
PageName = Literal["Dashboard", "Trades", "Unternehmen", "Admin", "Einstellungen", "Methodik", "Trade-Detail", "Unternehmens-Detail"]

HEADER_NAV_OPTIONS: dict[str, str] = {
    "📊 Dashboard": "Dashboard",
    "🧾 Trades": "Trades",
    "🏢 Unternehmen": "Unternehmen",
}

SIDEBAR_NAV_OPTIONS: dict[str, str] = {
    "📘 Methodik": "Methodik",
    "⚙️ Einstellungen": "Einstellungen",
    "🛠️ Admin": "Admin",
}

DETAIL_PAGES = {"Trade-Detail", "Unternehmens-Detail"}
HEADER_PAGES = set(HEADER_NAV_OPTIONS.values())


def _resolve_parent_target(nav_target: str) -> str:
    """Leitet Detailseiten auf ihre Parent-Seite für den Navbar-Active-State ab."""

    if nav_target == "Trade-Detail":
        return "Trades"
    if nav_target == "Unternehmens-Detail":
        return "Unternehmen"
    return nav_target


def _render_navbar_control(options_list: list[str], current_label: str) -> str:
    """Rendert eine saubere Navbar-Steuerung ohne Radio-/Checkbox-Optik."""

    if hasattr(st, "segmented_control"):
        selected = st.segmented_control(
            "Navigation",
            options=options_list,
            default=current_label if current_label in options_list else options_list[0],
            selection_mode="single",
            label_visibility="collapsed",
            key="main_navbar",
        )
        return str(selected) if selected else options_list[0]

    # Fallback für ältere Streamlit-Versionen.
    return st.radio(
        "Navigation",
        options=options_list,
        index=options_list.index(current_label) if current_label in options_list else 0,
        horizontal=True,
        label_visibility="collapsed",
    )


def _set_nav_target(target: PageName) -> None:
    if st.session_state.get("nav_target") == target:
        return
    st.session_state["nav_target"] = target
    st.rerun()

def render_navigation_topbar() -> PageName:
    """Rendert die Hauptnavigation als obere Navbar."""

    # Bestimme aktuelle Seite aus Session State oder Default.
    if "nav_target" not in st.session_state:
        st.session_state["nav_target"] = "Dashboard"

    parent_target = _resolve_parent_target(str(st.session_state["nav_target"]))
    current_label = next(
        (k for k, v in HEADER_NAV_OPTIONS.items() if v == parent_target),
        list(HEADER_NAV_OPTIONS.keys())[0],
    )
    options_list = list(HEADER_NAV_OPTIONS.keys())

    with st.container(border=True):
        left, right = st.columns([1.2, 2.8], vertical_alignment="center")
        with left:
            st.markdown("<div class='mercator-topbar-eyebrow'>Operative Arbeitsbereiche</div>", unsafe_allow_html=True)
            st.markdown("<div class='mercator-topbar-title'>Mercator Control Center</div>", unsafe_allow_html=True)
        with right:
            selected_label = _render_navbar_control(options_list, current_label)

    # Update nav_target nur für Header-Seiten, damit Sidebar-Ziele stabil bleiben.
    new_target = HEADER_NAV_OPTIONS[selected_label]
    if st.session_state["nav_target"] in HEADER_PAGES and st.session_state["nav_target"] != new_target:
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


def render_sidebar_navigation() -> None:
    """Rendert sekundäre Seiten in der linken Sidebar als ausklappbare Navigation."""

    active_target = _resolve_parent_target(str(st.session_state.get("nav_target", "Dashboard")))

    with st.sidebar:
        st.markdown("### Arbeitsbereiche")
        with st.expander("Verwaltung & Hilfe", expanded=False):
            for label, target in SIDEBAR_NAV_OPTIONS.items():
                button_type: Literal["primary", "secondary", "tertiary"] = (
                    "primary" if active_target == target else "secondary"
                )
                if st.button(label, key=f"sidebar_nav_{target}", use_container_width=True, type=button_type):
                    _set_nav_target(target)  # type: ignore[arg-type]


def render_system_status_sidebar(db_status, mysql_res):
    """Rendert den System-Status in der Sidebar."""
    with st.sidebar:
        st.markdown("---")
        with st.expander("System-Status", expanded=True):
            mysql_color = "green" if db_status.mysql.is_connected else "red"
            mysql_label = "MySQL: Online" if db_status.mysql.is_connected else "MySQL: Offline"
            st.markdown(f":{mysql_color}[{mysql_label}]")
            if mysql_res and mysql_res.active_target:
                st.caption(f"Target: {mysql_res.active_target}")

            mongo_color = "green" if db_status.mongo.is_connected else "red"
            mongo_label = "MongoDB: Online" if db_status.mongo.is_connected else "MongoDB: Offline"
            st.markdown(f":{mongo_color}[{mongo_label}]")

            mode_label = "Betriebsmodus: Schreiben aktiv" if db_status.is_write_mode_available else "Betriebsmodus: Lesemodus"
            st.caption(mode_label)
            if not db_status.is_settings_persistence_available:
                st.caption("Einstellungen: nur Sitzung")
