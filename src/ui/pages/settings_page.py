"""Einstellungen-Seite für globale App-Parameter."""

from __future__ import annotations

import streamlit as st
from src.services.app_settings_service import AppSettingsService, RuntimeSettings
from src.domain_rules import ScoreGatePolicy
from src.preprocessing.gate_evaluator import GATE_FAIL, GATE_PASS, GATE_PENDING
from src.ui.components.context_bar import render_context_bar
from src.ui.components.page_scaffold import render_error_state, render_page_header

def render_settings_page(runtime_settings_service: AppSettingsService) -> None:
    """Rendert die zentralen App-Einstellungen mit Fokus auf Fachlogik (Requirement 8.1)."""
    render_page_header("Einstellungen", "Konfiguration der fachlichen Analyse-Parameter, Gate-Regeln und Scoring-Logik.")

    runtime_settings = runtime_settings_service.load()
    policy = runtime_settings_service.load_score_gate_policy()

    # Tabs für Fachbereiche
    tab_gates, tab_score, tab_explanation = st.tabs([
        "🎯 Gates", "📊 Scoring-Schwellen", "📖 Logik-Erklärung"
    ])

    with tab_gates:
        st.subheader("Gate-Einschränkungen")
        st.caption("Definition der harten Ausschlusskriterien für den Dashboard-Scope.")
        
        with st.form("gate_settings_form", border=True):
            g1, g2 = st.columns(2)
            min_trade_value = g1.number_input(
                "Mindest-Trade-Wert ($)", 
                min_value=0, 
                value=int(policy.gate_min_trade_value),
                help="Trades unter diesem Wert werden im Pre-Gate aussortiert."
            )
            gate_form_type = g2.text_input(
                "Erforderlicher Form Type", 
                value=policy.gate_form_type_required,
                help="Standardmäßig '4' für Insider-Trades."
            )

            s1, s2 = st.columns(2)
            gate_security_name = s1.text_input(
                "Erforderlicher Security Name (Teilstring)", 
                value=policy.gate_security_name_required,
                help="Filtert nach Titeln (z.B. 'Common Stock')."
            )
            gate_validation = s2.selectbox(
                "Erforderlicher Validierungs-Status", 
                options=["VALID", "INVALID", "UNCHECKED"], 
                index=0 if policy.gate_validation_status_required == "VALID" else 1,
                help="Legt fest, ob nur technisch valide Trades durchgelassen werden."
            )

            a1, a2 = st.columns(2)
            allowed_aod = a1.text_input(
                "Erlaubte Transaktions-Codes (CSV)", 
                value=",".join(policy.gate_allowed_acquisition_or_disposition),
                help="Z.B. 'A' für Acquisition (Kauf), 'D' für Disposition (Verkauf)."
            )
            excluded_tt = a2.text_input(
                "Ausgeschlossene Transaktions-Typen (CSV)", 
                value=",".join(policy.gate_excluded_transaction_types),
                help="Z.B. 'A-Award', 'M-Exempt' (Gratis-Zuteilungen)."
            )

            if st.form_submit_button("Gate-Einstellungen speichern", type="primary", use_container_width=True):
                new_policy = ScoreGatePolicy(
                    score_threshold_fail_max=policy.score_threshold_fail_max,
                    score_threshold_hold_min=policy.score_threshold_hold_min,
                    score_threshold_pass_min=policy.score_threshold_pass_min,
                    fail_label=policy.fail_label,
                    hold_label=policy.hold_label,
                    pass_label=policy.pass_label,
                    fail_color=policy.fail_color,
                    hold_color=policy.hold_color,
                    pass_color=policy.pass_color,
                    gate_validation_status_required=gate_validation,
                    gate_form_type_required=gate_form_type,
                    gate_security_name_required=gate_security_name,
                    gate_allowed_acquisition_or_disposition=tuple(v.strip().upper() for v in allowed_aod.split(",") if v.strip()),
                    gate_excluded_transaction_types=tuple(v.strip() for v in excluded_tt.split(",") if v.strip()),
                    gate_min_trade_value=int(min_trade_value)
                )
                runtime_settings_service.save_score_gate_policy(new_policy)
                st.success("Gate-Einstellungen erfolgreich gespeichert.")
                st.rerun()

    with tab_score:
        st.subheader("Scoring-Klassifizierung")
        st.caption("Schwellenwerte für die Zuweisung der Trade-Klassen (A, B, C, D, E) basierend auf dem Mercator-Score.")
        
        with st.form("score_settings_form", border=True):
            st.markdown("#### Schwellenwerte (Score 0-100)")
            t1, t2, t3 = st.columns(3)
            # Hinweis: Wir nutzen hier die Policy-Werte für PASS/HOLD/FAIL
            th_pass = t1.number_input("PASS (Grün) ab", min_value=0.0, max_value=100.0, value=policy.score_threshold_pass_min, help="Mindest-Score für Status PASS.")
            th_hold = t2.number_input("HOLD (Gelb) ab", min_value=0.0, max_value=100.0, value=policy.score_threshold_hold_min, help="Mindest-Score für Status HOLD.")
            th_fail = t3.number_input("FAIL (Rot) bis", min_value=0.0, max_value=100.0, value=policy.score_threshold_fail_max, help="Maximal-Score für Status FAIL.")

            if st.form_submit_button("Scoring-Einstellungen speichern", type="primary", use_container_width=True):
                new_policy = ScoreGatePolicy(
                    score_threshold_fail_max=th_fail,
                    score_threshold_hold_min=th_hold,
                    score_threshold_pass_min=th_pass,
                    fail_label=policy.fail_label,
                    hold_label=policy.hold_label,
                    pass_label=policy.pass_label,
                    fail_color=policy.fail_color,
                    hold_color=policy.hold_color,
                    pass_color=policy.pass_color,
                    gate_validation_status_required=policy.gate_validation_status_required,
                    gate_form_type_required=policy.gate_form_type_required,
                    gate_security_name_required=policy.gate_security_name_required,
                    gate_allowed_acquisition_or_disposition=policy.gate_allowed_acquisition_or_disposition,
                    gate_excluded_transaction_types=policy.gate_excluded_transaction_types,
                    gate_min_trade_value=policy.gate_min_trade_value
                )
                runtime_settings_service.save_score_gate_policy(new_policy)
                st.success("Scoring-Einstellungen erfolgreich gespeichert.")
                st.rerun()

    with tab_explanation:
        st.subheader("📖 Die Mercator Scoring-Logik")
        st.markdown("""
        Der Mercator-Score ist ein diskretes Punktesystem (0-100), das die Relevanz eines Insider-Trades bewertet.
        
        ### 1. Trade Value (max. 50 Punkte)
        Bedeutung: Das investierte Volumen.
        - **50 Pkt:** >= $10.000.000
        - **40 Pkt:** >= $1.000.000
        - **30 Pkt:** >= $500.000
        - **20 Pkt:** >= $100.000
        - **10 Pkt:** >= $50.000
        
        ### 2. Direction (max. 20 Punkte)
        Bedeutung: Käufe werden deutlich stärker gewichtet als Verkäufe.
        - **20 Pkt:** KAUF (Acquisition)
        - **5 Pkt:** VERKAUF (Disposition)
        
        ### 3. Insider Role (max. 20 Punkte)
        Bedeutung: Operative Nähe des Insiders zum Unternehmen.
        - **20 Pkt:** CEO, CFO, Officer oder President
        - **15 Pkt:** Director
        - **5 Pkt:** Sonstige (z.B. 10% Owner)
        
        ### 4. Market Cap (max. 5 Punkte)
        Bedeutung: Trades in Large Caps gelten als belastbarer.
        - **5 Pkt:** Marktkapitalisierung >= $1 Mrd.
        
        ### 5. Validation (max. 5 Punkte)
        Bedeutung: Technische Datenqualität.
        - **5 Pkt:** Status ist VALID
        
        ---
        **Klassen-Zuweisung:**
        - **A (Top Relevanz):** >= 80 Punkte
        - **B (Hohe Relevanz):** >= 60 Punkte
        - **C (Mittlere Relevanz):** >= 40 Punkte
        - **D (Geringe Relevanz):** >= 20 Punkte
        - **E (Vernachlässigbar):** < 20 Punkte
        """)
