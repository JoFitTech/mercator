"""Dashboard-Seite als reine Overview-Seite (Requirement 3)."""

from __future__ import annotations
import pandas as pd
import streamlit as st
from datetime import date, timedelta
from src.config.settings import AppSettings
from src.services.app_settings_service import AppSettingsService
from src.services.database_status_service import DatabaseStatus
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService
from src.ui.components.context_bar import render_filter_chip_bar, render_status_bar
from src.ui.components.page_scaffold import render_kpi_row, render_page_header

def render_dashboard_page(
    service: DashboardService | None,
    import_service: ImportService | None = None,
    settings: AppSettings | None = None,
    runtime_settings_service: AppSettingsService | None = None,
    db_status: DatabaseStatus | None = None,
) -> None:
    """Rendert das Dashboard als reinen Marktüberblick."""
    if service is None:
        st.warning(
            "Dashboard derzeit nicht verfügbar, da MySQL nicht erreichbar ist. "
            "Bitte nutzen Sie Methodik oder Einstellungen im Lesemodus."
        )
        return

    # 1. Header (kein Import mehr hier)
    # Requirement 5.6: render_page_header ist verpflichtend.
    render_page_header("Markt-Dashboard", "Zusammenfassung der Insider-Aktivitäten.")
    
    # 2. Zeitraum / Context (Requirement 2.1: transaction_date)
    if "dashboard_filters" not in st.session_state:
        st.session_state.dashboard_filters = {
            "date_range": (date.today() - timedelta(days=30), date.today())
        }
    
    with st.container(border=True):
        date_range = st.date_input(
            "Analyse-Zeitraum (basiert auf Transaktionsdatum)",
            value=st.session_state.dashboard_filters["date_range"],
            help="Filtert alle Metriken nach dem Datum des Insider-Trades."
        )
        st.session_state.dashboard_filters["date_range"] = date_range

    filters = {
        "date_from": date_range[0] if isinstance(date_range, (list, tuple)) and len(date_range) > 0 else None,
        "date_to": date_range[1] if isinstance(date_range, (list, tuple)) and len(date_range) > 1 else None
    }

    # 3. Daten laden
    with st.spinner("Lade Übersicht..."):
        payload = service.build_dashboard_payload(filters=filters)

    # Requirement 5.7: Spezialisierte Komponenten statt generischer context_bar
    render_filter_chip_bar(active_filters={"Zeitraum": f"{filters['date_from']} bis {filters['date_to']}"})
    render_status_bar(last_update=payload.get("last_update"))

    # 4. KPI-Bereich
    st.markdown("#### Kennzahlen (Dashboard-Valide Trades)")
    kpis = [
        {"label": "Trades (Heute)", "value": str(payload.get("trades_today", 0)), "help": "Anzahl Trades heute (transaction_date)."},
        {"label": "Trades (7 Tage)", "value": str(payload.get("trades_7d", 0)), "help": "Anzahl Trades letzte 7 Tage."},
        {"label": "Trades (30 Tage)", "value": str(payload.get("trades_30d", 0)), "help": "Anzahl Trades letzte 30 Tage."},
        {"label": "Gesamtvolumen", "value": f"${payload.get('total_volume', 0):,.0f}", "help": "Summe der Volumen aller validen Trades."},
    ]
    render_kpi_row(kpis)

    # 5. Diagramm-Bereich
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Sektor-Verteilung")
        df_buy = payload.get("sector_distribution_buy", pd.DataFrame())
        if not df_buy.empty:
            st.markdown("**Top BUY Sektoren**")
            st.bar_chart(df_buy.set_index("sector")["count"].head(5))
    with c2:
        st.subheader("Marktaktivität")
        df_activity = payload.get("timeline_distribution", pd.DataFrame())
        if not df_activity.empty:
            pivot = df_activity.pivot(index="event_date", columns="direction", values="count").fillna(0)
            st.line_chart(pivot)

    # 6. Vorschau (Requirement 3.5)
    st.markdown("---")
    st.subheader("Letzte 10 Insider-Aktivitäten (akkumuliert)")
    preview_df = payload.get("preview_trades", pd.DataFrame())
    if preview_df.empty:
        st.info("Keine aktuellen Aktivitäten im Zeitraum.")
    else:
        # Spaltenbereinigung
        p_df = preview_df.copy()
        for col in ["symbol_at_trade", "reporting_name", "acquisition_or_disposition", "accumulated_trade_value_estimated", "score", "accumulation_start_date"]:
            if col not in p_df.columns: p_df[col] = None

        display_cols = ["symbol_at_trade", "reporting_name", "acquisition_or_disposition", "accumulated_trade_value_estimated", "score", "accumulation_start_date"]
        st.dataframe(
            p_df[display_cols],
            column_config={
                "symbol_at_trade": "Symbol",
                "reporting_name": "Insider",
                "acquisition_or_disposition": "Richtung",
                "accumulated_trade_value_estimated": st.column_config.NumberColumn("Wert", format="$%d"),
                "score": st.column_config.NumberColumn("Score", format="%.0f"),
                "accumulation_start_date": st.column_config.DateColumn("Datum", format="DD.MM.YY")
            },
            use_container_width=True,
            hide_index=True
        )

    # 7. CTA
    if st.button("Zur operativen Trades-Arbeitsfläche", type="primary", use_container_width=True):
        st.session_state["nav_target"] = "Trades"
        st.rerun()
