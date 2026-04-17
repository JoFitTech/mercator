"""Dashboard-Seite mit KPIs und fokussierten Überblicksvisualisierungen."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config.settings import AppSettings
from src.preprocessing.gate_evaluator import GATE_FAIL, GATE_PASS, GATE_PENDING
from src.services.app_settings_service import AppSettingsService, RuntimeSettings
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService
from src.ui.components.context_bar import render_context_bar
from src.ui.components.page_scaffold import render_kpi_row, render_page_header, render_warning_state
from src.ui.components.tables import render_trade_table


EMPTY_DATA_MESSAGE = (
    "Es sind aktuell noch keine verarbeiteten Daten verfügbar. "
    "Lade zuerst Daten oder prüfe den Datenbankstatus."
)


def _render_runtime_preferences(runtime_settings_service: AppSettingsService, runtime_settings: RuntimeSettings) -> None:
    with st.expander("Analyse- und Gate-Defaults", expanded=False):
        c1, c2, c3 = st.columns(3)
        min_trade_value = c1.number_input("min_trade_value", min_value=0, value=runtime_settings.min_trade_value)
        require_purchase_event = c2.checkbox("require_purchase_event", value=runtime_settings.require_purchase_event)
        require_common_stock = c3.checkbox("require_common_stock", value=runtime_settings.require_common_stock)

        a1, a2 = st.columns(2)
        allowed_aod = a1.text_input(
            "allowed acquisition_or_disposition (CSV)", value=",".join(runtime_settings.allowed_acquisition_or_disposition)
        )
        allowed_tt = a2.text_input("allowed transaction_type (CSV)", value=",".join(runtime_settings.allowed_transaction_types))

        b1, b2, b3 = st.columns([1, 1, 1])
        filter_statuses = b1.multiselect(
            "profile_gate_filter_statuses", options=[GATE_PASS, GATE_PENDING, GATE_FAIL], default=list(runtime_settings.profile_gate_filter_statuses)
        )
        ttl_days = b2.number_input("profile_ttl_days", min_value=1, max_value=365, value=runtime_settings.profile_ttl_days)
        lookup_mode = b3.selectbox(
            "lookup_mode",
            options=["cik_primary_symbol_fallback", "symbol_only"],
            index=0 if runtime_settings.lookup_mode == "cik_primary_symbol_fallback" else 1,
        )

        s1, s2 = st.columns(2)
        if s1.button("Einstellungen speichern", use_container_width=True):
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
        if s2.button("Defaults wiederherstellen", use_container_width=True):
            runtime_settings_service.reset()
            st.success("Defaults aus .env wiederhergestellt.")


@st.cache_data(ttl=60)
def _get_dashboard_payload(_service: DashboardService, target: str) -> dict:
    """Holt Dashboard-Daten mit Cache (TTL 60s)."""
    return _service.build_dashboard_payload()


def render_dashboard_page(
    service: DashboardService | None,
    import_service: ImportService | None = None,
    settings: AppSettings | None = None,
    runtime_settings_service: AppSettingsService | None = None,
) -> None:
    """Rendert das Dashboard als zentrale Hauptzentrale."""
    
    # 1. Page Header
    render_page_header(
        "Dashboard", 
        "Systemzustand, Datenabdeckung und Marktmuster.",
        actions=[{"label": "Refresh", "type": "primary"}]
    )

    if service is None:
        st.warning("MySQL nicht erreichbar. Analysefunktionen sind eingeschränkt.")
        return

    # Daten laden
    target = settings.mysql.mysql_active_target if settings else "default"
    payload = _get_dashboard_payload(service, target)

    # 2. Context Bar
    render_context_bar(
        active_filters=["Gesamtmarkt"],
        last_update=payload.get("last_update"),
        mysql_target=target,
    )

    if payload["clean_records"] == 0 and payload["raw_records"] == 0:
        st.warning(EMPTY_DATA_MESSAGE)
        return

    # 3. KPI Row
    kpi_data = [
        {"label": "Valid Trades", "value": f"{payload['clean_records']:,}"},
        {"label": "Gate Passed", "value": f"{payload.get('gate_pass_records', 0):,}"},
        {"label": "Profile", "value": f"{payload['company_profiles']:,}"},
    ]
    
    if not payload["trades"].empty:
        counts = payload["trades"]["direction"].value_counts()
        buy_c = int(counts.get("BUY", 0))
        total = len(payload["trades"])
        ratio = buy_c / total if total else 0
        kpi_data.append({"label": "BUY-Quote", "value": f"{ratio:.0%}"})
        
        avg_score = payload["trades"]["score"].mean() if "score" in payload["trades"].columns else 0
        kpi_data.append({"label": "Ø Score", "value": f"{avg_score:.2f}"})

    render_kpi_row(kpi_data)

    st.markdown("---")

    # 4. Primary Work Area (Charts)
    st.subheader("Marktentwicklung & Muster")
    c1, c2 = st.columns([0.65, 0.35])
    
    with c1:
        st.caption("Trade Value über Zeit")
        if not payload["buy_sell_volume"].empty:
            chart_df = payload["buy_sell_volume"].set_index("event_date")
            st.area_chart(chart_df, height=350, use_container_width=True)
        else:
            st.info("Keine Zeitreihendaten verfügbar.")

    with c2:
        st.caption("Sektorverteilung (Top 10)")
        if not payload["sector_distribution"].empty:
            sector_df = payload["sector_distribution"].sort_values("count", ascending=False).head(10)
            st.bar_chart(sector_df.set_index("sector"), horizontal=True, height=350, use_container_width=True)
        else:
            st.info("Keine Sektordaten verfügbar.")

    st.markdown("---")

    # 5. Secondary Insight Area (Table)
    st.subheader("Top-Gelegenheiten (Vorschau)")
    if not payload["trades"].empty:
        trades_df = payload["trades"].sort_values(by="score", ascending=False).head(10)
        render_trade_table(trades_df, height=400)
    else:
        st.info("Keine Trades zur Anzeige verfügbar.")
