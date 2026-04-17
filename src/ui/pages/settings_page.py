"""Einstellungen-Seite für globale App-Parameter."""

from __future__ import annotations

import streamlit as st
from src.services.app_settings_service import AppSettingsService, RuntimeSettings
from src.preprocessing.gate_evaluator import GATE_FAIL, GATE_PASS, GATE_PENDING
from src.ui.components.context_bar import render_context_bar
from src.ui.components.page_scaffold import render_error_state, render_page_header

def render_settings_page(runtime_settings_service: AppSettingsService) -> None:
    """Rendert die zentralen App-Einstellungen."""
    render_page_header("Einstellungen", "Konfiguration globaler Analyse-Parameter, Gate-Regeln und System-Präferenzen.")

    render_context_bar(active_filters=["System-Config"])

    runtime_settings = runtime_settings_service.load()

    with st.container(border=True):
        st.subheader("Analyse-Parameter")
        c1, c2 = st.columns(2)
        min_trade_value = c1.number_input(
            "Mindest-Trade-Wert ($)", 
            min_value=0, 
            value=runtime_settings.min_trade_value,
            help="Trades unter diesem Wert werden im Pre-Gate aussortiert."
        )
        lookup_mode = c2.selectbox(
            "Profil-Lookup Modus",
            options=["cik_primary_symbol_fallback", "symbol_only"],
            index=0 if runtime_settings.lookup_mode == "cik_primary_symbol_fallback" else 1,
            help="cik_primary_symbol_fallback: Nutzt CIK für stabilere Verknüpfung (empfohlen). symbol_only: Schnellerer Match nur über Ticker."
        )

        st.markdown("---")
        st.subheader("Gate-Einschränkungen")
        g1, g2 = st.columns(2)
        require_purchase_event = g1.toggle(
            "Nur Käufe (Acquisition) zulassen", 
            value=runtime_settings.require_purchase_event
        )
        require_common_stock = g2.toggle(
            "Nur Common Stock zulassen", 
            value=runtime_settings.require_common_stock
        )

        a1, a2 = st.columns(2)
        allowed_aod = a1.text_input(
            "Erlaubte Transaktions-Codes (CSV)", 
            value=",".join(runtime_settings.allowed_acquisition_or_disposition),
            help="Z.B. A für Acquisition, D für Disposition"
        )
        allowed_tt = a2.text_input(
            "Erlaubte Transaktions-Typen (CSV)", 
            value=",".join(runtime_settings.allowed_transaction_types),
            help="Z.B. P-Purchase, S-Sale"
        )

        st.markdown("---")
        st.subheader("Caching & Enrichment")
        b1, b2 = st.columns(2)
        filter_statuses = b1.multiselect(
            "Profile laden für Gate-Status", 
            options=[GATE_PASS, GATE_PENDING, GATE_FAIL], 
            default=list(runtime_settings.profile_gate_filter_statuses)
        )
        ttl_days = b2.number_input(
            "Profil-Cache TTL (Tage)", 
            min_value=1, 
            max_value=365, 
            value=runtime_settings.profile_ttl_days
        )

        st.markdown("---")
        s1, s2 = st.columns(2)
        if s1.button("Einstellungen speichern", type="primary", use_container_width=True):
            try:
                runtime_settings_service.save(
                    RuntimeSettings(
                        min_trade_value=int(min_trade_value),
                        require_purchase_event=require_purchase_event,
                        require_common_stock=require_common_stock,
                        allowed_acquisition_or_disposition=tuple(v.strip().upper() for v in allowed_aod.split(",") if v.strip()),
                        allowed_transaction_types=tuple(v.strip() for v in allowed_tt.split(",") if v.strip()),
                        profile_gate_filter_statuses=tuple(filter_statuses),
                        profile_ttl_days=int(ttl_days or 1),
                        lookup_mode=lookup_mode,
                    )
                )
                st.success("Einstellungen erfolgreich gespeichert.")
                st.rerun()
            except Exception as e:
                render_error_state(f"Fehler beim Speichern: {e}")

        if s2.button("Auf System-Defaults zurücksetzen", use_container_width=True):
            runtime_settings_service.reset()
            st.info("Einstellungen auf Werkseinstellungen zurückgesetzt.")
            st.rerun()

    st.markdown("---")
    st.subheader("Experten-Einstellungen")
    
    def on_settings_advanced_mode_change():
        val = st.session_state["advanced_mode_settings_toggle"]
        st.session_state["advanced_mode"] = val
        # Sync mit Sidebar-Widget-Key (wird beim nächsten Rerun übernommen)
        st.session_state["advanced_mode_toggle"] = val

    st.toggle(
        "Advanced Mode aktivieren", 
        value=st.session_state.get("advanced_mode", False),
        key="advanced_mode_settings_toggle",
        on_change=on_settings_advanced_mode_change,
        help="Schaltet zusätzliche Debug-Informationen und DB-Management-Tools frei (z.B. im Admin-Bereich)."
    )
