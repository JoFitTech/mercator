"""Navigations-Logik für Mercator (Requirement 5.1)."""

from __future__ import annotations
import base64
from functools import lru_cache
from pathlib import Path
from typing import Literal

import streamlit as st

from src.services.public_share_service import TunnelManager, TunnelStatus

# Typer-Definition für Seiten
PageName = Literal["Dashboard", "Trades", "Unternehmen", "Admin", "Einstellungen", "Trade-Detail", "Unternehmens-Detail"]

HEADER_NAV_OPTIONS: dict[str, str] = {
    "Dashboard": "Dashboard",
    "Trades": "Trades",
    "Unternehmen": "Unternehmen",
}

SIDEBAR_NAV_OPTIONS: dict[str, str] = {
    "Methodik": "Methodik",
    "Einstellungen": "Einstellungen",
    "Admin": "Admin",
}

DETAIL_PAGES = {"Trade-Detail", "Unternehmens-Detail"}
HEADER_PAGES = set(HEADER_NAV_OPTIONS.values())
SIDEBAR_PAGES = set(SIDEBAR_NAV_OPTIONS.values())
ALL_NAV_TARGETS: set[str] = HEADER_PAGES | set(SIDEBAR_NAV_OPTIONS.values()) | DETAIL_PAGES


def public_share_sidebar_status_text(status: TunnelStatus) -> str:
    return {
        TunnelStatus.RUNNING: "Läuft",
        TunnelStatus.WARNING: "Läuft (Warnung)",
        TunnelStatus.STARTING: "Startet …",
        TunnelStatus.STALE: "Stale",
        TunnelStatus.ERROR: "Fehler",
        TunnelStatus.STOPPED: "Gestoppt",
    }.get(status, "Gestoppt")


def _resolve_parent_target(nav_target: str) -> str:
    """Leitet Detailseiten auf ihre Parent-Seite für den Navbar-Active-State ab."""

    if nav_target == "Trade-Detail":
        return "Trades"
    if nav_target == "Unternehmens-Detail":
        return "Unternehmen"
    return nav_target


def _render_navbar_control(options_list: list[str], current_label: str) -> tuple[str, str | None]:
    """Rendert die Header-Navigation als explizite Buttons."""

    selected_label = current_label if current_label in options_list else options_list[0]
    clicked_label: str | None = None
    cols = st.columns(len(options_list))
    for option, col in zip(options_list, cols):
        button_type: Literal["primary", "secondary", "tertiary"] = "primary" if option == selected_label else "secondary"
        if col.button(option, key=f"main_navbar_{option}", use_container_width=True, type=button_type):
            selected_label = option
            clicked_label = option
    return selected_label, clicked_label


def _set_nav_target(target: PageName) -> None:
    """Atomic navigation state setter mit Rückfall auf validen Target."""
    current = str(st.session_state.get("nav_target") or "")
    if current == target:
        return
    if target not in ALL_NAV_TARGETS:
        target = "Dashboard"
    st.session_state["nav_target"] = target
    st.rerun()


def ensure_valid_nav_target(default_target: PageName = "Dashboard") -> PageName:
    """Sichert den Navigationszustand gegen ungültige oder veraltete Werte ab."""
    raw_target = st.session_state.get("nav_target")
    if raw_target is None:
        st.session_state["nav_target"] = default_target
        return default_target

    current_target = str(raw_target)
    if current_target not in ALL_NAV_TARGETS:
        st.session_state["nav_target"] = default_target
        return default_target
    return current_target  # type: ignore[return-value]


def _resolve_header_active_target(current_target: str, previous_header_target: str) -> str:
    """Liefert den sichtbaren Header-Active-State ohne Sidebar-Ziele zu überschreiben."""
    parent_target = _resolve_parent_target(current_target)
    if parent_target in HEADER_PAGES:
        return parent_target
    if previous_header_target in HEADER_PAGES:
        return previous_header_target
    return "Dashboard"


def _determine_header_nav_update(
    current_target: str,
    selected_header_target: str,
    previous_header_target: str,
    clicked_header_target: str | None = None,
) -> str | None:
    """Ermittelt, ob die Header-Auswahl das globale Nav-Target ändern darf."""
    parent_target = _resolve_parent_target(current_target)

    if current_target in HEADER_PAGES or current_target in DETAIL_PAGES:
        if selected_header_target != parent_target:
            return selected_header_target
        return None

    if current_target in SIDEBAR_PAGES:
        # Sidebar-Seiten bleiben stabil, bis die Header-Auswahl wirklich geändert wurde.
        if clicked_header_target in HEADER_PAGES:
            return clicked_header_target
        if selected_header_target != previous_header_target:
            return selected_header_target
        return None

    return "Dashboard"


def _should_reset_header_widget(
    current_target: str,
    widget_value: str | None,
    previous_header_target: str,
) -> bool:
    """Verhindert stale Widget-Werte, die Sidebar-Ziele fälschlich überschreiben könnten."""
    if current_target not in SIDEBAR_PAGES:
        return False
    if not widget_value:
        return False
    return widget_value in HEADER_PAGES and widget_value != previous_header_target


def render_navigation_topbar() -> PageName:
    """Rendert die Hauptnavigation als obere Navbar."""

    # Bestimme aktuelle Seite aus Session State oder Default.
    ensure_valid_nav_target()

    current_target = str(st.session_state["nav_target"])
    previous_header_target = str(st.session_state.get("header_nav_target", "Dashboard"))
    active_header_target = _resolve_header_active_target(current_target, previous_header_target)
    current_label = next(
        (k for k, v in HEADER_NAV_OPTIONS.items() if v == active_header_target),
        list(HEADER_NAV_OPTIONS.keys())[0],
    )
    options_list = list(HEADER_NAV_OPTIONS.keys())

    with st.container():
        left, right = st.columns([0.32, 3.68], vertical_alignment="center")
        with left:
            _render_topbar_brand()
        with right:
            selected_label, clicked_label = _render_navbar_control(options_list, current_label)

    selected_header_target = HEADER_NAV_OPTIONS[selected_label]
    st.session_state["header_nav_target"] = selected_header_target
    clicked_header_target = HEADER_NAV_OPTIONS.get(clicked_label) if clicked_label else None
    nav_update = _determine_header_nav_update(
        current_target,
        selected_header_target,
        previous_header_target,
        clicked_header_target=clicked_header_target,
    )
    if nav_update:
        _set_nav_target(nav_update)  # type: ignore[arg-type]

    # Zurück-Button für Detailseiten.
    if st.session_state["nav_target"] in DETAIL_PAGES:
        if st.button("Zurück zur Liste", key="top_nav_back_to_list"):
            if st.session_state["nav_target"] == "Trade-Detail":
                st.session_state["nav_target"] = "Trades"
            else:
                st.session_state["nav_target"] = "Unternehmen"
            st.rerun()

    return st.session_state["nav_target"]


def _resolve_favicon_path() -> Path | None:
    favicon_path = Path(__file__).resolve().parents[2] / "assets" / "favicon" / "favicon.png"
    return favicon_path if favicon_path.exists() else None


@lru_cache(maxsize=1)
def _favicon_data_url() -> str | None:
    favicon_path = _resolve_favicon_path()
    if favicon_path is None:
        return None
    favicon_bytes = bytearray(favicon_path.read_bytes())
    favicon_b64 = base64.standard_b64encode(favicon_bytes).decode("ascii")  # type: ignore[arg-type]
    return f"data:image/png;base64,{favicon_b64}"


def _render_topbar_brand() -> None:
    """Rendert das Favicon im Header statt des Eyebrow-Texts."""
    data_url = _favicon_data_url()
    if data_url is None:
        st.markdown("<div class='mercator-topbar-brand' aria-hidden='true'></div>", unsafe_allow_html=True)
        return

    st.markdown(
        f"""
        <div class="mercator-topbar-brand" style="display:flex; align-items:center; gap:0.6rem;">
            <img src="{data_url}" alt="Mercator" class="mercator-topbar-logo" style="width:40px; height:40px;" />
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_public_share_sidebar_controls() -> None:
    manager = st.session_state.get("public_share_manager")
    enabled = bool(st.session_state.get("public_share_enabled"))
    execution_mode = str(st.session_state.get("public_share_execution_mode", "host"))
    if not enabled:
        return
    if execution_mode == "host":
        with st.expander("Öffentliche Freigabe (Tools)", expanded=False):
            st.caption("Host-Modus aktiv: Steuerung erfolgt über PowerShell.")
            st.code(".\\mercator.ps1 share-start\n.\\mercator.ps1 share-status", language="powershell")
            if st.button("Im Admin verwalten", key="sidebar_public_share_admin_host", use_container_width=True):
                _set_nav_target("Admin")
        return
    if not isinstance(manager, TunnelManager):
        return

    session = manager.get_session()
    status = session.status if session else TunnelStatus.STOPPED

    with st.expander("Öffentliche Freigabe (Tools)", expanded=False):
        st.caption("Nur Steuerungstools – keine eigenständige Seite.")
        status_text = public_share_sidebar_status_text(status)
        st.caption(f"Status: {status_text}")
        if session and session.error_message:
            st.caption(f"Hinweis: {session.error_message}")

        running_like = status in {TunnelStatus.RUNNING, TunnelStatus.WARNING, TunnelStatus.STARTING}
        primary_label = "Freigabe stoppen" if running_like else "Freigabe starten"
        if st.button(primary_label, key="sidebar_public_share_primary", use_container_width=True, type="primary"):
            if running_like:
                manager.stop()
            else:
                manager.start()
            st.rerun()

        can_open = bool(session and session.status in {TunnelStatus.RUNNING, TunnelStatus.WARNING} and session.public_url)
        st.link_button(
            "Öffnen",
            session.public_url if can_open and session and session.public_url else "http://localhost",
            disabled=not can_open,
            use_container_width=True,
        )

        if st.button("Im Admin verwalten", key="sidebar_public_share_admin", use_container_width=True):
            _set_nav_target("Admin")


def render_sidebar_navigation() -> None:
    """Rendert sekundäre Seiten in der linken Sidebar als ausklappbare Navigation."""

    active_target = _resolve_parent_target(str(st.session_state.get("nav_target", "Dashboard")))

    with st.sidebar:
        st.markdown("## Mercator")
        st.markdown("### Arbeitsbereiche")
        st.caption("Sekundärnavigation: Bereich aufklappen und Ziel auswählen.")
        with st.expander("Verwaltung & Hilfe", expanded=False):
            st.caption("Container mit Unterseiten – kein eigener Navigationspunkt.")
            for label, target in SIDEBAR_NAV_OPTIONS.items():
                button_type: Literal["primary", "secondary", "tertiary"] = (
                    "primary" if active_target == target else "secondary"
                )
                if st.button(label, key=f"sidebar_nav_{target}", use_container_width=True, type=button_type):
                    _set_nav_target(target)  # type: ignore[arg-type]
        # Public-Share-Steuerung bewusst nur im Admin-Bereich.


def render_system_status_sidebar(db_status, mysql_res):
    """Rendert den System-Status in der Sidebar."""
    with st.sidebar:
        with st.expander("System-Status", expanded=True):
            mysql_color = "green" if db_status.mysql.is_connected else "red"
            mysql_label = "MySQL: Online" if db_status.mysql.is_connected else "MySQL: Offline"
            st.markdown(f":{mysql_color}[{mysql_label}]")
            if mysql_res and mysql_res.active_target:
                st.caption(f"Target: {mysql_res.active_target}")

            mongo_color = "green" if db_status.mongo.is_connected else "red"
            mongo_label = "MongoDB: Online" if db_status.mongo.is_connected else "MongoDB: Offline"
            st.markdown(f":{mongo_color}[{mongo_label}]")
            if db_status.mongo.active_target:
                st.caption(f"Mongo Target: {db_status.mongo.active_target}")
            if db_status.mongo.used_fallback:
                st.caption("Mongo Fallback: aktiv")
            if db_status.mongo.requested_target == "uni" and db_status.mongo.active_target == "local" and db_status.mongo.used_fallback:
                st.caption("Uni-Datenbank nicht erreichbar. Lokaler Praesentationsmodus aktiv.")
            elif db_status.mongo.messages:
                prefix = "Hinweis" if db_status.mongo.is_connected else "Grund"
                short_message = str(db_status.mongo.messages[0]).split("\n", 1)[0][:140]
                st.caption(f"{prefix}: {short_message}")
                with st.expander("Details", expanded=False):
                    for msg in db_status.mongo.messages:
                        st.code(str(msg), language="text")

            mode_label = "Betriebsmodus: Schreiben aktiv" if db_status.is_write_mode_available else "Betriebsmodus: Lesemodus"
            st.caption(mode_label)
            if not db_status.is_settings_persistence_available:
                st.caption("Einstellungen: nur Sitzung")
