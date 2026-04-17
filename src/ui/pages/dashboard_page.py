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


# Helper und Sub-Komponenten entfernt, da nun zentral in Admin/Settings.


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
    """Rendert das Dashboard als Marktüberblick (Aggregierte KPIs & Trends)."""
    
    if service is None:
        st.warning("MySQL nicht erreichbar. Dashboard ist deaktiviert.")
        return

    # 1. HEADER
    render_dashboard_header(import_service)
    
    # 2. EINSTELLUNGSBEREICH (Deaktiviert, da nun in Admin/Settings)
    # render_dashboard_settings_panel(runtime_settings_service)

    # 3. MARKT-SCOPE (Datumseinschränkung)
    filters = render_dashboard_scope_bar(service)
    
    # 3b. DATEN LADEN
    with st.spinner("Lade Marktüberblick..."):
        payload = service.build_dashboard_payload(filters=filters)

    # 3c. CONTEXT BAR (Stand & Target)
    render_context_bar(
        active_filters=st.session_state.filters,
        last_update=payload.get("last_update") or date.today().strftime("%d.%m.%Y"),
        mysql_target=st.session_state.get("mysql_runtime_target", "local")
    )

    # 4. KPI-BEREICH (2 Zeilen à 4 Karten)
    render_dashboard_kpis(payload)

    # 4b. DIAGNOSE-BLOCK
    render_dashboard_diagnostics(payload)

    # 5. DIAGRAMME: SEKTOR- UND AKTIVITÄTSÜBERSICHT
    c1, c2 = st.columns([0.4, 0.6])
    with c1:
        render_sector_distribution_block(payload)
    with c2:
        render_trade_activity_chart(payload)

    # 6. ÜBERSICHTSTABELLE (Kompakte Vorschau)
    st.markdown("### Jüngste Markt-Aktivitäten")
    render_dashboard_table(payload)
    
    # CTA zur Trades-Seite
    st.info("Hinweis: Für detaillierte Analysen, Filterung und Sortierung nutzen Sie bitte die [Trades-Seite](/Trades).")


def render_dashboard_header(import_service: ImportService | None) -> None:
    """Rendert den Dashboard-Header mit Titel und globalen Aktionen."""
    st.markdown("""
        <style>
        .stTitle h1 { margin-top: 0 !important; margin-bottom: 0 !important; padding-top: 0 !important; }
        </style>
    """, unsafe_allow_html=True)

    col_title, col_actions = st.columns([0.6, 0.4], vertical_alignment="center")
    with col_title:
        st.markdown('<h1 style="margin: 0;">Markt-Dashboard</h1>', unsafe_allow_html=True)
        st.caption("Aggregierte Übersicht über alle Insider-Aktivitäten.")
    
    with col_actions:
        # Zwei Buttons auf gleicher Höhe: Refresh und Import
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            if st.button("Refresh", use_container_width=True, help="Dashboard Scope aktualisieren"):
                st.rerun()
        
        with btn_col2:
            if st.button("Import", use_container_width=True, type="secondary", help="Daten von API laden"):
                if import_service:
                    with st.status("Import läuft...") as status:
                        try:
                            import_service.run_hourly_import()
                            status.update(label="Import abgeschlossen", state="complete")
                            st.toast("Import erfolgreich abgeschlossen")
                            st.rerun()
                        except Exception as e:
                            status.update(label=f"Fehler: {e}", state="error")
                            st.error(f"Import fehlgeschlagen: {e}")
                else:
                    st.error("Import-Service nicht verfügbar")


# Dashboard Settings Panel entfernt.


def render_dashboard_scope_bar(service: DashboardService) -> dict:
    """Rendert den Markt-Scope (Zeitraum) und optionale Filter."""
    if "filters" not in st.session_state:
        st.session_state.filters = {
            "symbol": "",
            "insider": "",
            "date_range": (date.today() - timedelta(days=30), date.today()),
            "sector": "All"
        }

    with st.container(border=True):
        c1, c2 = st.columns([0.4, 0.6])
        with c1:
            date_range = st.date_input(
                "Markt-Zeitraum",
                value=st.session_state.filters.get("date_range"),
                help="Legt den Zeitbereich für die Dashboard-Metriken fest."
            )
        with c2:
            with st.expander("Zusätzliche Markt-Filter (Optional)"):
                f1, f2, f3 = st.columns(3)
                symbol = f1.text_input("Symbol", value=st.session_state.filters.get("symbol", ""))
                insider = f2.text_input("Insider", value=st.session_state.filters.get("insider", ""))
                all_sectors = ["All"] + service.company_repo.fetch_all_sectors()
                current_sector = st.session_state.filters.get("sector", "All")
                sector_index = all_sectors.index(current_sector) if current_sector in all_sectors else 0
                sector = f3.selectbox("Sektor", options=all_sectors, index=sector_index)

    # Sync
    st.session_state.filters.update({
        "symbol": symbol, "insider": insider, "date_range": date_range, "sector": sector
    })

    # Filter-Dict für Service bauen
    filters = {}
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


def render_dashboard_diagnostics(payload: dict) -> None:
    """Rendert einen Diagnose-Block für Datenqualitäts-Probleme."""
    warning_reason = payload.get("dashboard_warning_reason")
    empty_reason = payload.get("dashboard_empty_reason")
    
    if empty_reason:
        st.info(empty_reason)
        return

    if warning_reason:
        with st.container(border=True):
            st.warning(f"**Datenqualität:** {warning_reason}")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Scoped", payload.get("scoped_trades_count", 0))
            c2.metric("Valid", payload.get("valid_trades_count", 0))
            c3.metric("Invalid", payload.get("invalid_trades_count", 0))
            c4.metric("Unresolved", payload.get("unresolved_sector_count", 0))
            c5.metric("Missing", payload.get("missing_sector_count", 0))
            
            with st.expander("Details zur Datenqualität"):
                st.write(f"- **Fehlender Preis:** {payload.get('missing_price_count', 0)} Trades")
                st.write(f"- **Fehlende Menge:** {payload.get('missing_qty_count', 0)} Trades")
                st.write(f"- **Unbekannte Richtung:** {payload.get('unknown_direction_count', 0)} Trades")
                st.info("Hinweis: Trades benötigen ein Symbol, einen Sektor (resolved), Preis > 0, Menge > 0 und eine gültige Richtung (BUY/SELL), um in KPIs und Charts berücksichtigt zu werden.")

def render_dashboard_kpis(payload: dict) -> None:
    """Rendert zwei KPI-Zeilen für Marktaktivität und Qualität."""
    st.markdown("#### Markt-Aktivität")
    kpi_activity = [
        {"label": "Heute", "value": f"{payload.get('trades_today', 0):,}", "help": "Anzahl der Insider-Trades mit heutigem Transaktionsdatum."},
        {"label": "Letzte 7 Tage", "value": f"{payload.get('trades_7d', 0):,}", "help": "Summe aller Trades in der letzten Woche."},
        {"label": "Letzte 30 Tage", "value": f"{payload.get('trades_30d', 0):,}", "help": "Summe aller Trades im letzten Monat."},
        {"label": "Gesamtvolumen", "value": f"${payload.get('total_volume', 0.0):,.0f}", "help": "Geschätztes Gesamtvolumen (Preis * Menge) aller validen Dashboard-Trades."},
    ]
    render_kpi_row(kpi_activity)
    
    st.markdown("#### Validität & Richtung")
    kpi_quality = [
        {"label": "Valid Dashboard", "value": f"{payload.get('valid_trades_count', 0):,}", "help": "Anzahl der Trades, die alle Kriterien für die Dashboard-Anzeige erfüllen (Symbol, Sektor, Preis, Menge)."},
        {"label": "Gate Passed", "value": f"{payload.get('gate_passed_count', 0):,}", "help": "Anzahl der Trades, die die harten Ausschlusskriterien (Gate) bestanden haben."},
        {"label": "BUY Quote", "value": f"{payload.get('buy_quote', 0.0):.1%}", "help": "Prozentualer Anteil der Käufe an allen validen Trades."},
        {"label": "SELL Quote", "value": f"{payload.get('sell_quote', 0.0):.1%}", "help": "Prozentualer Anteil der Verkäufe an allen validen Trades."},
    ]
    render_kpi_row(kpi_quality)
    
    # Ø Score als kleiner Zusatz falls relevant
    avg_score = payload.get("avg_score", 0.0)
    if avg_score > 0:
        st.caption(f"Durchschnittlicher Score im aktuellen Scope: {avg_score:.2f} (höher ist besser)")


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
    st.subheader("Übersicht Trades im Scope")
    
    trades_all = payload.get("trades_all_scoped", pd.DataFrame())
    trades_valid = payload.get("trades_valid", pd.DataFrame())
    trades_invalid = payload.get("trades_invalid", pd.DataFrame())
    
    if trades_all.empty:
        st.info("Keine Trades gefunden")
        return

    # View Toggle & Action Row
    c_toggle, c_deepdive = st.columns([0.6, 0.4], vertical_alignment="center")
    
    with c_toggle:
        view_mode = st.radio(
            "Tabellenansicht",
            options=["Alle im Scope", "Nur Valid", "Nur Invalid"],
            horizontal=True,
            label_visibility="collapsed",
            key="dashboard_table_view_mode"
        )
    
    if view_mode == "Nur Valid":
        display_df = trades_valid
    elif view_mode == "Nur Invalid":
        display_df = trades_invalid
    else:
        display_df = trades_all

    if display_df.empty:
        st.info(f"Keine Daten für Filter '{view_mode}' vorhanden.")
        return

    # Spaltenreihenfolge für Dashboard (kompakt)
    display_cols = [
        "dashboard_valid", "symbol_at_trade", "reporting_name", "direction",
        "trade_value_estimated", "score_value", "gate_status", "transaction_date"
    ]
    
    # Sicherstellen dass alle existieren
    for col in display_cols:
        if col not in display_df.columns:
            if col == "score_value" and "score" in display_df.columns:
                display_df["score_value"] = display_df["score"]
            elif col == "transaction_date" and "transaction_date" not in display_df.columns and "filing_date" in display_df.columns:
                display_df["transaction_date"] = display_df["filing_date"]
            else:
                display_df[col] = None

    col_config = {
        "dashboard_valid": st.column_config.CheckboxColumn("Valid", width="small", help="Erfüllt Dashboard-Kriterien"),
        "symbol_at_trade": st.column_config.TextColumn("Symbol", width="small"),
        "reporting_name": st.column_config.TextColumn("Insider", width="medium"),
        "direction": st.column_config.TextColumn("Richtung", width="small"),
        "trade_value_estimated": st.column_config.NumberColumn("Value", format="$%d"),
        "score_value": st.column_config.NumberColumn("Score", format="%.1f"),
        "gate_status": st.column_config.TextColumn("Gate"),
        "transaction_date": st.column_config.DateColumn("Date", format="DD.MM.YY"),
    }
    
    # Render table mit Auswahl
    event = st.dataframe(
        display_df[display_cols],
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
        selected_row = display_df.iloc[selected_idx]
        selected_symbol = selected_row.get("symbol_at_trade")
        if selected_symbol:
            st.session_state["selected_ticker"] = selected_symbol
            with c_deepdive:
                if st.button(f"Deep-Dive für {selected_symbol} öffnen", type="primary", use_container_width=True):
                    # In Streamlit 1.35+ switch_page ist verfügbar. 
                    # Falls nicht, reicht st.session_state und manueller Wechsel.
                    try:
                        st.switch_page(st.session_state.nav_pages["Unternehmen"])
                    except Exception:
                        st.toast(f"Ticker {selected_symbol} ausgewählt. Bitte wechseln Sie zum Tab 'Unternehmen'.")
