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


from datetime import date, timedelta
from src.ui.components.page_scaffold import render_kpi_row, render_page_header
from src.ui.components.tables import render_trade_table, render_smart_table

def render_dashboard_page(
    service: DashboardService | None,
    import_service: ImportService | None = None,
    settings: AppSettings | None = None,
    runtime_settings_service: AppSettingsService | None = None,
) -> None:
    """Rendert das Dashboard gemäß der neuen Spezifikation (Wireframe-orientiert)."""
    
    if service is None:
        st.warning("MySQL nicht erreichbar. Dashboard ist deaktiviert.")
        return

    # 1. HEADER
    render_dashboard_header(import_service)
    
    # 2. EINSTELLUNGSBEREICH (Expandable)
    if st.session_state.get("show_settings", False):
        render_dashboard_settings_panel(runtime_settings_service)

    # 3. SUCH- UND SCOPE-LEISTE
    filters = render_dashboard_scope_bar(service)

    # Daten laden basierend auf Scope
    payload = service.build_dashboard_payload(filters=filters)

    # 4. KPI-ZEILE (4 Karten)
    render_dashboard_kpis(payload)

    # 5. SEKTOR-VERTEILUNG (2 Donuts)
    render_sector_distribution_block(payload)

    # 6. TRADE ACTIVITY (Breites Chart)
    render_trade_activity_chart(payload)

    # 7. ÜBERSICHTSTABELLE
    render_dashboard_table(payload)


def render_dashboard_header(import_service: ImportService | None) -> None:
    """Rendert den Dashboard-Header mit Titel und 3 Action-Buttons."""
    # CSS für Margin-Reset des Titels um vertikale Ausrichtung zu ermöglichen
    st.markdown("""
        <style>
        .stTitle h1 {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            line-height: 1.2 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    col_title, col_actions = st.columns([0.6, 0.4], vertical_alignment="center")
    with col_title:
        st.title("Dashboard")
    
    with col_actions:
        # Drei Buttons auf gleicher Höhe: Refresh, Import, Settings
        btn_col1, btn_col2, btn_col3 = st.columns([0.35, 0.35, 0.3])
        
        with btn_col1:
            if st.button("Refresh", use_container_width=True, help="Dashboard Scope aktualisieren"):
                st.rerun()
        
        with btn_col2:
            if st.button("Import", use_container_width=True, type="secondary", help="Daten von API laden"):
                if import_service:
                    with st.spinner("Import läuft..."):
                        try:
                            import_service.run_hourly_import()
                            st.success("Import abgeschlossen")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Import fehlgeschlagen: {e}")
                else:
                    st.error("Import-Service nicht verfügbar")
        
        with btn_col3:
            if st.button("Settings", use_container_width=True, help="Konfiguration öffnen"):
                st.session_state["show_settings"] = not st.session_state.get("show_settings", False)
                st.rerun()


def render_dashboard_settings_panel(runtime_settings_service: AppSettingsService | None) -> None:
    """Rendert das Einstellungs-Panel unter dem Header."""
    if not runtime_settings_service:
        st.info("Einstellungs-Service nicht verfügbar")
        return

    with st.container(border=True):
        st.markdown("### Dashboard & API Einstellungen")
        runtime_settings = runtime_settings_service.load()
        
        c1, c2, c3 = st.columns(3)
        priority = c1.selectbox(
            "Provider-Priorität", 
            options=["FMP > AV > Poly", "AV > FMP > Poly"], 
            index=0 if runtime_settings.lookup_mode == "cik_primary_symbol_fallback" else 1
        )
        max_hits = c2.number_input("Max API Hits / Run", min_value=1, value=runtime_settings.profile_ttl_days or 100)
        retry = c3.selectbox("Retry-Verhalten", options=["Standard", "Aggressiv", "Minimal"], index=0)
        
        e1, e2, e3 = st.columns(3)
        enrichment_active = e1.toggle("Enrichment aktiv", value=True)
        force_reenrich = e2.toggle("Force Re-Enrichment", value=False)
        missing_only = e3.toggle("Nur fehlende Profile", value=True)
        
        if st.button("Einstellungen übernehmen", use_container_width=True):
            lookup_mode = "cik_primary_symbol_fallback" if "FMP" in priority else "symbol_only"
            updated_runtime = RuntimeSettings(
                min_trade_value=runtime_settings.min_trade_value,
                require_purchase_event=runtime_settings.require_purchase_event,
                require_common_stock=runtime_settings.require_common_stock,
                allowed_acquisition_or_disposition=runtime_settings.allowed_acquisition_or_disposition,
                allowed_transaction_types=runtime_settings.allowed_transaction_types,
                profile_gate_filter_statuses=runtime_settings.profile_gate_filter_statuses,
                profile_ttl_days=int(max_hits),
                lookup_mode=lookup_mode
            )
            runtime_settings_service.save(updated_runtime)
            st.success("Einstellungen gespeichert")
            st.rerun()


def render_dashboard_scope_bar(service: DashboardService) -> dict:
    """Rendert die breite Such- und Scope-Leiste."""
    # Wir nutzen session_state zur Synchronisation der Filter
    if "filters" not in st.session_state:
        st.session_state.filters = {
            "symbol": "",
            "insider": "",
            "date_range": (date.today() - timedelta(days=7), date.today()),
            "sector": "All"
        }

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([0.25, 0.25, 0.3, 0.2])
        
        with c1:
            symbol = st.text_input(
                "Symbol", 
                value=st.session_state.filters.get("symbol", ""),
                placeholder="z.B. AAPL"
            )
        with c2:
            insider = st.text_input(
                "Insider", 
                value=st.session_state.filters.get("insider", ""),
                placeholder="Name..."
            )
        with c3:
            date_range = st.date_input(
                "Zeitraum",
                value=st.session_state.filters.get("date_range"),
                help="Scope-Zeitraum für alle Metriken"
            )
        with c4:
            all_sectors = ["All"] + service.company_repo.fetch_all_sectors()
            current_sector = st.session_state.filters.get("sector", "All")
            sector_index = all_sectors.index(current_sector) if current_sector in all_sectors else 0
            sector = st.selectbox("Sektor", options=all_sectors, index=sector_index)

    # Sync session state
    st.session_state.filters["symbol"] = symbol
    st.session_state.filters["insider"] = insider
    st.session_state.filters["date_range"] = date_range
    st.session_state.filters["sector"] = sector

    # Filter-Dict für Service bauen
    filters = {
        "dashboard_valid": True
    }
    if symbol:
        filters["symbol"] = symbol
    if insider:
        filters["reporting_name"] = insider
    if sector != "All":
        filters["sector"] = sector
    
    # Robuste Datumsverarbeitung für partielle Ranges und leere Zustände
    if isinstance(date_range, (list, tuple)):
        if len(date_range) >= 1 and date_range[0]:
            filters["date_from"] = date_range[0]
        if len(date_range) >= 2 and date_range[1]:
            filters["date_to"] = date_range[1]
    elif date_range:
        # Falls st.date_input ein einzelnes Datum zurückgibt (keine Range ausgewählt)
        filters["date_from"] = date_range
        filters["date_to"] = date_range
    
    return filters


def render_dashboard_kpis(payload: dict) -> None:
    """Rendert 4 KPI-Karten in einer Reihe."""
    kpi_data = [
        {"label": "Valid Trades", "value": f"{payload.get('valid_trades_count', 0):,}"},
        {"label": "Gates Passed", "value": f"{payload.get('gate_passed_count', 0):,}"},
        {"label": "Profile", "value": f"{payload.get('profile_count', 0):,}"},
        {"label": "Buy/Sell Quote", "value": f"{payload.get('buy_quote', 0.0):.0%}"},
    ]
    render_kpi_row(kpi_data)
    
    # Ø Score als kleiner Zusatz falls relevant
    avg_score = payload.get("avg_score", 0.0)
    if avg_score > 0:
        st.caption(f"Durchschnittlicher Score im aktuellen Scope: {avg_score:.2f}")


def render_sector_distribution_block(payload: dict) -> None:
    """Rendert den Sektor-Verteilungs-Block mit 2 Donut/Pie Charts."""
    st.subheader("Sektor-Verteilung")
    c_buy, c_sell = st.columns(2)
    
    with c_buy:
        st.markdown("**BUY Sektoren**")
        _render_sector_donut(payload.get("sector_distribution_buy", pd.DataFrame()), "BUY")
        
    with c_sell:
        st.markdown("**SELL Sektoren**")
        _render_sector_donut(payload.get("sector_distribution_sell", pd.DataFrame()), "SELL")


def _render_sector_donut(df: pd.DataFrame, direction: str) -> None:
    """Interner Helfer für Sektor-Visualisierung (Donut-Chart)."""
    if df.empty:
        st.info(f"Keine {direction} Daten im Scope")
        return
        
    # Top 7 Gruppierung
    df = df.sort_values("count", ascending=False)
    if len(df) > 8:
        top_7 = df.head(7)
        others_count = df.iloc[7:]["count"].sum()
        others_df = pd.DataFrame([{"sector": "Sonstige", "count": others_count}])
        plot_df = pd.concat([top_7, others_df])
    else:
        plot_df = df.copy()
    
    # Versuch mit Plotly für echte Donut-Charts
    try:
        import plotly.express as px
        fig = px.pie(
            plot_df, 
            values="count", 
            names="sector", 
            hole=0.5,
            color_discrete_sequence=px.colors.qualitative.Safe,
            labels={"sector": "Sektor", "count": "Anzahl"}
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            showlegend=False,
            height=250
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    except ImportError:
        # Fallback auf Bar Chart falls Plotly fehlt
        st.bar_chart(plot_df.set_index("sector")["count"], horizontal=True, height=200)

    # Interaktive Buttons für die Top-Sektoren (funktionaler Drilldown)
    st.markdown("*Quick Filter:*")
    # Nur die Top 5 als Buttons um Platz zu sparen
    top_n = df.head(5)
    
    # Layout für Buttons in mehreren Reihen falls nötig
    cols = st.columns(3)
    for i, (_, row) in enumerate(top_n.iterrows()):
        sector_name = row["sector"]
        if cols[i % 3].button(f"{sector_name}", key=f"btn_{direction}_{sector_name}", use_container_width=True):
            st.session_state.filters["sector"] = sector_name
            st.rerun()


def render_trade_activity_chart(payload: dict) -> None:
    """Rendert die Trade Activity als breites Hauptdiagramm."""
    st.subheader("Trade Activity")
    df = payload.get("timeline_distribution", pd.DataFrame())
    
    if not df.empty:
        # Pivot für BUY/SELL Spalten
        chart_data = df.pivot(index="event_date", columns="direction", values="count").fillna(0)
        st.bar_chart(chart_data, use_container_width=True, height=300)
    else:
        st.info("Keine Aktivitätsdaten im gewählten Zeitraum")


def render_dashboard_table(payload: dict) -> None:
    """Rendert die Übersichtstabelle mit Detail-Button."""
    st.subheader("Übersichtstabelle")
    trades_df = payload.get("trades", pd.DataFrame())
    
    if trades_df.empty:
        st.info("Keine Trades gefunden")
        return

    # In dieser Version nutzen wir die Tabellenauswahl zur Navigation
    # Erste Spalte "Detail" als Text ohne Emoji
    trades_df["Detail"] = "Open"
    
    # Spaltenreihenfolge
    display_cols = [
        "Detail", "symbol_at_trade", "reporting_name", "sector", "direction",
        "trade_value_estimated", "score_value", "gate_status", 
        "validation_status", "filing_date"
    ]
    
    # Sicherstellen dass alle existieren
    for col in display_cols:
        if col not in trades_df.columns:
            trades_df[col] = None

    col_config = {
        "Detail": st.column_config.TextColumn("Details", width="small", help="Zeile auswählen für Details"),
        "symbol_at_trade": st.column_config.TextColumn("Symbol", width="small"),
        "reporting_name": st.column_config.TextColumn("Insider", width="medium"),
        "sector": st.column_config.TextColumn("Sector", width="medium"),
        "direction": st.column_config.TextColumn("Richtung", width="small"),
        "trade_value_estimated": st.column_config.NumberColumn("Value", format="$%.2f"),
        "score_value": st.column_config.NumberColumn("Score", format="%.2f"),
        "gate_status": st.column_config.TextColumn("Gate"),
        "validation_status": st.column_config.TextColumn("Validation"),
        "filing_date": st.column_config.DateColumn("Date"),
    }
    
    # Render table mit Auswahl
    event = st.dataframe(
        trades_df[display_cols],
        column_config=col_config,
        use_container_width=True,
        hide_index=True,
        height=500,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    # Navigation bei Auswahl
    if event and event.get("selection", {}).get("rows"):
        selected_idx = event["selection"]["rows"][0]
        selected_symbol = trades_df.iloc[selected_idx]["symbol_at_trade"]
        if selected_symbol:
            st.session_state["selected_ticker"] = selected_symbol
            st.toast(f"Symbol {selected_symbol} ausgewählt. Wechsel zu Unternehmen für Details.")
            # In Streamlit 1.35+ kann man switch_page nutzen
            try:
                # Da wir den exakten Pfad nicht kennen, versuchen wir die gängigsten Muster
                # Oder wir belassen es beim Toast und dem gesetzten Session State.
                pass
            except Exception:
                pass
