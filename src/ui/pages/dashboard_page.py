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

def _build_dashboard_filters(date_range: tuple[date, date] | list[date] | tuple[date, ...]) -> dict[str, date | None]:
    """Normalisiert den Dashboard-Zeitraum robust in ``date_from``/``date_to``."""
    if isinstance(date_range, tuple | list):
        date_from = date_range[0] if len(date_range) > 0 else None
        date_to = date_range[1] if len(date_range) > 1 else date_from
    else:
        date_from = None
        date_to = None
    return {"date_from": date_from, "date_to": date_to}


def _format_period_label(filters: dict[str, date | None]) -> str:
    """Formatiert einen stabilen Zeitraum ohne `None`-Artefakte."""
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if date_from and date_to:
        return f"{date_from.strftime('%d.%m.%Y')} bis {date_to.strftime('%d.%m.%Y')}"
    if date_from:
        return f"ab {date_from.strftime('%d.%m.%Y')}"
    if date_to:
        return f"bis {date_to.strftime('%d.%m.%Y')}"
    return "Gesamter verfügbarer Zeitraum"


def _navigate_to_trades() -> None:
    """Setzt deterministisch das Navigationsziel und triggert einen Rerun."""
    st.session_state["nav_target"] = "Trades"
    st.rerun()


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

    filters = _build_dashboard_filters(date_range)

    # 3. Daten laden
    with st.spinner("Lade Übersicht..."):
        payload = service.build_dashboard_payload(filters=filters)

    # Requirement 5.7: Spezialisierte Komponenten statt generischer context_bar
    period_label = _format_period_label(filters)
    render_filter_chip_bar(active_filters={"Zeitraum": period_label})
    st.caption(f"Alle Kennzahlen und Diagramme berücksichtigen nur Trades im Zeitraum: {period_label}.")
    render_status_bar(last_update=payload.get("last_update"))

    # 4. KPI-Bereich
    st.markdown("#### Kennzahlen (Dashboard-Valide Trades)")
    kpis = [
        {"label": "Trades im Zeitraum", "value": str(payload.get("scoped_trades_count", 0)), "help": "Alle Trades im aktuell gewählten Zeitraum."},
        {"label": "Dashboard-valide", "value": str(payload.get("valid_trades_count", 0)), "help": "Trades, die alle Dashboard-Kriterien erfüllen."},
        {"label": "Gate PASS", "value": str(payload.get("gate_passed_count", 0)), "help": "Anzahl Trades mit Gate-Status PASS."},
        {"label": "Gesamtvolumen (valide)", "value": f"${payload.get('total_volume', 0):,.0f}", "help": "Summe des Volumens dashboard-valider Trades."},
    ]
    render_kpi_row(kpis)

    # 5. Diagramm-Bereich
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Sektor-Verteilung")
        st.caption("Top-Sektoren der BUY-Transaktionen im gewählten Zeitraum.")
        df_buy = payload.get("sector_distribution_buy", pd.DataFrame())
        if not df_buy.empty:
            st.markdown("**Top BUY Sektoren**")
            st.bar_chart(df_buy.set_index("sector")["count"].head(5))
    with c2:
        st.subheader("Marktaktivität")
        st.caption("Zeitverlauf der BUY/SELL-Anzahl im gewählten Zeitraum.")
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
    if st.button("Zur operativen Trades-Arbeitsfläche", type="primary", use_container_width=True, key="dashboard_to_trades_cta"):
        _navigate_to_trades()
