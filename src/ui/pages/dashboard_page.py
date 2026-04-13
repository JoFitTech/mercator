"""Dashboard-Seite mit KPIs und Basisvisualisierungen."""

from __future__ import annotations

import streamlit as st

from src.config.settings import AppSettings
from src.preprocessing.gate_evaluator import GATE_FAIL, GATE_PASS, GATE_PENDING
from src.services.app_settings_service import AppSettingsService, RuntimeSettings
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService


EMPTY_DATA_MESSAGE = (
    "Es sind aktuell noch keine verarbeiteten Daten verfügbar. "
    "Lade zunächst einen Datensatz oder prüfe die Datenbankverbindung."
)


def render_dashboard_page(
    service: DashboardService | None,
    import_service: ImportService | None = None,
    settings: AppSettings | None = None,
    runtime_settings_service: AppSettingsService | None = None,
) -> None:
    """Rendert KPI-Karten und Diagramme für den Gesamtüberblick."""
    st.title("Mercator")
    st.markdown("### Dashboard")
    st.caption("Überblick über importierte Datensätze, Kennzahlen und erste Analyseergebnisse.")

    advanced_mode = st.session_state.get("advanced_mode", False)

    runtime_settings = runtime_settings_service.load() if runtime_settings_service else None
    if runtime_settings is not None and settings is not None:
        with st.expander("Gate- und Profil-Einstellungen", expanded=False):
            c1, c2, c3 = st.columns(3)
            min_trade_value = c1.number_input("min_trade_value", min_value=0, value=runtime_settings.min_trade_value)
            require_purchase_event = c2.checkbox("require_purchase_event", value=runtime_settings.require_purchase_event)
            require_common_stock = c3.checkbox("require_common_stock", value=runtime_settings.require_common_stock)
            allowed_aod = st.text_input(
                "allowed acquisition_or_disposition (CSV)", value=",".join(runtime_settings.allowed_acquisition_or_disposition)
            )
            allowed_tt = st.text_input(
                "allowed transaction_type (CSV)", value=",".join(runtime_settings.allowed_transaction_types)
            )
            filter_statuses = st.multiselect("profile_gate_filter_statuses", options=[GATE_PASS, GATE_PENDING, GATE_FAIL], default=list(runtime_settings.profile_gate_filter_statuses))
            ttl_days = st.number_input("profile_ttl_days", min_value=1, max_value=365, value=runtime_settings.profile_ttl_days)
            lookup_mode = st.selectbox("lookup_mode", options=["cik_primary_symbol_fallback", "symbol_only"], index=0 if runtime_settings.lookup_mode == "cik_primary_symbol_fallback" else 1)
            b1, b2 = st.columns(2)
            if b1.button("Einstellungen speichern", use_container_width=True):
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
                st.success("Einstellungen gespeichert.")
            if b2.button("Defaults wiederherstellen", use_container_width=True):
                runtime_settings_service.reset()
                st.success("Defaults aus .env wiederhergestellt.")

    if settings is not None:
        with st.expander("Import-Steuerung & Konfiguration", expanded=advanced_mode):
            st.subheader("FMP API Import")
            c1, c2 = st.columns(2)
            page = c1.number_input(
                "Feed-Seite (Standard: 0)", min_value=0, step=1, value=settings.fmp.default_feed_page
            )
            limit = c2.number_input(
                "Feed-Limit (Standard: 100)", min_value=1, max_value=1000, step=10, value=settings.fmp.default_feed_limit
            )

            status_options = [GATE_PASS, GATE_PENDING, GATE_FAIL]
            selected_statuses = st.multiselect(
                "Gate-Status für Profil-Anreicherung (API 2)",
                options=status_options,
                default=list((runtime_settings.profile_gate_filter_statuses if runtime_settings else settings.fmp.profile_gate_filter_statuses)),
                help="Profil-Abfrage erfolgt nur für Trades mit diesen Statuswerten.",
            )

            if advanced_mode:
                st.info(
                    "Gate-Regeln (Read-only): min_trade_value=%s, require_purchase=%s, require_common_stock=%s"
                    % (
                        runtime_settings.min_trade_value if runtime_settings else settings.gate.min_trade_value,
                        runtime_settings.require_purchase_event if runtime_settings else settings.gate.require_purchase_event,
                        runtime_settings.require_common_stock if runtime_settings else settings.gate.require_common_stock,
                    )
                )

            if st.button("Datenimport jetzt starten", type="primary", use_container_width=True):
                if import_service is None:
                    st.warning("Import derzeit nicht verfuegbar. Rohdatenspeicherung deaktiviert.")
                    error_detail = st.session_state.get("import_service_error")
                    if error_detail:
                        st.caption(f"Technischer Hinweis: {error_detail}")
                else:
                    with st.spinner("Import läuft..."):
                        summary = import_service.run_hourly_import(
                            page=int(page),
                            limit=int(limit),
                            profile_fetch_statuses=tuple(selected_statuses),
                        )
                    st.success(
                        "Import erfolgreich abgeschlossen: %s Rohdatensätze, %s Profile geladen."
                        % (summary.fetched_feed_records, summary.fetched_profiles)
                    )

    if service is None:
        st.warning("MySQL nicht erreichbar. Analysefunktionen eingeschränkt.")
        if import_service is None:
            st.info("Keine Datenverarbeitung verfügbar. Bitte Datenbankverbindungen prüfen.")
        return

    payload = service.build_dashboard_payload()

    if payload["clean_records"] == 0:
        st.warning(EMPTY_DATA_MESSAGE)
        return

    st.markdown("---")
    st.subheader("Zentrale Kennzahlen")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rohdaten (Mongo)", f"{payload['raw_records']:,}")
    c2.metric("Bereinigte Trades (MySQL)", f"{payload['clean_records']:,}")
    c3.metric("Unternehmensprofile", f"{payload['company_profiles']:,}")
    
    # Optional: Ein fiktiver Score oder eine zusätzliche Kennzahl
    pass_count = payload.get("gate_pass_records", 0)
    c4.metric("Gate-PASS", f"{pass_count:,}")

    st.markdown("---")
    st.subheader("Markttrends & Volumen")
    
    # 1. Chart: Kumuliertes Volumen BUY vs SELL über Zeit
    if not payload["buy_sell_volume"].empty:
        st.write("**Handelsvolumen pro Tag (Akkumuliert)**")
        # Line Chart für Buy/Sell Volumen
        chart_df = payload["buy_sell_volume"].set_index("event_date")
        st.area_chart(chart_df, height=300)

    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Sektoren-Verteilung")
        if not payload["sector_distribution"].empty:
            # Bar chart horizontal
            st.bar_chart(payload["sector_distribution"].set_index("sector"), horizontal=True)

    with col_right:
        st.subheader("Verhältnis Buy vs. Sell")
        # Donut Chart Ersatz (Pie ist in Streamlit nicht nativ, wir nehmen Bar oder Metrics)
        if not payload["trades"].empty:
            counts = payload["trades"]["direction"].value_counts()
            buy_c = counts.get("BUY", 0)
            sell_c = counts.get("SELL", 0)
            st.write(f"Transaktionen: **{buy_c} BUYS** vs **{sell_c} SELLS**")
            st.progress(buy_c / (buy_c + sell_c) if (buy_c + sell_c) > 0 else 0, text="Buy Ratio")

    if advanced_mode:
        st.markdown("---")
        st.subheader("Import-Historie")
        st.line_chart(payload["timeline_distribution"].set_index("e_date"))
