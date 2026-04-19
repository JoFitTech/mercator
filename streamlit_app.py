"""Einstiegspunkt der Streamlit-Anwendung Mercator (Requirement 1 & 5.1)."""

from __future__ import annotations
import streamlit as st

from src.app.bootstrap import bootstrap_app
from src.app.navigation import render_navigation_sidebar, render_system_status_sidebar
from src.app.auto_import import handle_auto_import, render_import_status_toast

from src.ui.pages.dashboard_page import render_dashboard_page
from src.ui.pages.trades_page import render_trades_page
from src.ui.pages.companies_page import render_companies_page
from src.ui.pages.company_detail_page import render_company_detail_page
from src.ui.pages.trade_detail_page import render_trade_detail_page
from src.ui.pages.admin_page import render_admin_page
from src.ui.pages.settings_page import render_settings_page
from src.ui.pages.methodology_page import render_methodology_page

def main():
    """Haupt-Einstiegspunkt der Anwendung."""
    
    # 1. Bootstrap (Config, Layout, Theme, Services)
    # Requirement 1: Radikal entschlackt, nur noch Bootstrap & Initialisierung.
    settings, db_status, mysql_res, factory = bootstrap_app()
    
    # 2. Sidebar Navigation & Status
    # Requirement 5.1: Navigation & Systemstatus in eigene Module ausgelagert.
    # P1.2: advanced_mode zentral in session_state schreiben, damit alle Seiten konsistent lesen können
    if "advanced_mode" not in st.session_state:
        st.session_state["advanced_mode"] = False
    advanced_mode = st.sidebar.toggle("Advanced Mode", value=st.session_state["advanced_mode"])
    st.session_state["advanced_mode"] = advanced_mode

    nav_target = render_navigation_sidebar()
    render_system_status_sidebar(db_status, mysql_res, advanced_mode=advanced_mode)

    # 3. Background Tasks (Auto-Import)
    # P0.3: Auto-Import folgt jetzt den RuntimeSettings (auto_import_enabled, interval, on_start)
    auto_import_blocked = bool(
        settings.disable_import or settings.review_mode or settings.ui_test_mode
    )
    if db_status.is_ingestion_available and not auto_import_blocked:
        runtime_settings = factory.create_app_settings_service().load()
        handle_auto_import(
            factory.create_import_service(),
            runtime=runtime_settings,
            disabled=auto_import_blocked,
        )
        render_import_status_toast()
        
    # 4. Page Routing (Page Dispatch)
    # Requirement 1: Klares Dispatching auf die Seitenmodule.
    if nav_target == "Dashboard":
        render_dashboard_page(
            service=factory.create_dashboard_service(),
            import_service=factory.create_import_service(),
            settings=settings,
            runtime_settings_service=factory.create_app_settings_service()
        )
    elif nav_target == "Trades":
        render_trades_page(factory.create_analysis_service())
    elif nav_target == "Unternehmen":
        render_companies_page(factory.create_company_repository())
    elif nav_target == "Einstellungen":
        render_settings_page(factory.create_app_settings_service())
    elif nav_target == "Methodik":
        render_methodology_page()
    elif nav_target == "Admin":
        render_admin_page(
            settings=settings,
            mysql_client=factory.mysql_client,
            mongo_available=db_status.mongo.is_connected,
            settings_service=factory.create_app_settings_service(),
            import_service=factory.create_import_service(),
            api_usage_service=factory.create_api_usage_service()
        )
    elif nav_target == "Trade-Detail":
        render_trade_detail_page(factory.create_analysis_service())
    elif nav_target == "Unternehmens-Detail":
        render_company_detail_page(factory.create_analysis_service())

if __name__ == "__main__":
    main()
