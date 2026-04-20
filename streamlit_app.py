"""Einstiegspunkt der Streamlit-Anwendung Mercator (Requirement 1 & 5.1)."""

from __future__ import annotations
import streamlit as st

from src.app.bootstrap import bootstrap_app
from src.app.infrastructure_mode import build_infrastructure_mode, render_infrastructure_banner
from src.app.navigation import render_navigation_topbar, render_sidebar_navigation, render_system_status_sidebar
from src.app.auto_import import handle_auto_import, render_import_status_toast
from src.services.public_share_service import CloudflareQuickTunnelProvider, TunnelManager, sync_public_share_sidebar_state

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
    infra_mode = build_infrastructure_mode(db_status)
    st.session_state["infra_mode"] = infra_mode
    
    # 2. Top-Navigation & Sidebar-Status
    # Requirement 5.1: Navigation & Systemstatus in eigene Module ausgelagert.
    nav_target = render_navigation_topbar()
    st.session_state["public_share_enabled"] = bool(settings.public_share.enabled)
    if settings.public_share.enabled and not isinstance(st.session_state.get("public_share_manager"), TunnelManager):
        st.session_state["public_share_manager"] = TunnelManager(
            provider=CloudflareQuickTunnelProvider(
                cloudflared_bin=settings.public_share.cloudflared_bin,
                startup_timeout_seconds=settings.public_share.startup_timeout_seconds,
                healthcheck_timeout_seconds=settings.public_share.healthcheck_timeout_seconds,
            ),
            provider_name=settings.public_share.provider,
            default_local_url=settings.public_share.local_url,
        )

    public_share_manager = st.session_state.get("public_share_manager")
    sync_public_share_sidebar_state(
        public_share_manager if isinstance(public_share_manager, TunnelManager) else None
    )
    render_sidebar_navigation()
    render_system_status_sidebar(db_status, mysql_res)
    render_infrastructure_banner(infra_mode)

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
            runtime_settings_service=factory.create_app_settings_service(),
            db_status=db_status,
        )
    elif nav_target == "Trades":
        render_trades_page(factory.create_analysis_service(), db_status=db_status)
    elif nav_target == "Unternehmen":
        render_companies_page(factory.create_company_repository(), db_status=db_status)
    elif nav_target == "Einstellungen":
        render_settings_page(factory.create_app_settings_service(), db_status=db_status)
    elif nav_target == "Methodik":
        render_methodology_page()
    elif nav_target == "Admin":
        render_admin_page(
            settings=settings,
            mysql_client=factory.mysql_client,
            mongo_available=db_status.mongo.is_connected,
            db_status=db_status,
            settings_service=factory.create_app_settings_service(),
            import_service=factory.create_import_service(),
            api_usage_service=factory.create_api_usage_service()
        )
    elif nav_target == "Trade-Detail":
        render_trade_detail_page(factory.create_analysis_service(), db_status=db_status)
    elif nav_target == "Unternehmens-Detail":
        render_company_detail_page(factory.create_analysis_service(), db_status=db_status)

if __name__ == "__main__":
    main()
