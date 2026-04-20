"""Unternehmen-Seite mit Fokus auf aktive Firmen (Requirement 6)."""

from __future__ import annotations
import pandas as pd
import streamlit as st
from src.db.repositories.company_repository import CompanyMySqlRepository
from src.services.database_status_service import DatabaseStatus
from src.ui.components.page_scaffold import (
    render_page_header,
    render_empty_state,
    render_kpi_row,
    safe_service_call,
    summarize_filters,
)

def render_companies_page(repository: CompanyMySqlRepository | None, db_status: DatabaseStatus | None = None) -> None:
    """Rendert die Unternehmens-Übersicht."""
    render_page_header("Unternehmen", "Übersicht aller Unternehmen mit registrierten Insider-Aktivitäten.")
    if repository is None:
        st.warning("Unternehmensdaten sind derzeit nicht verfügbar, da MySQL nicht erreichbar ist.")
        return

    # 1. Daten laden (nur aktive Firmen laut Requirement 6.1)
    with st.spinner("Lade Unternehmen..."):
        companies, error = safe_service_call(
            lambda: repository.list_active_companies(limit=1000),
            context_label="Unternehmensdaten",
            fallback=[],
        )
        if error is not None:
            st.warning("Unternehmen konnten nicht geladen werden. Bitte später erneut versuchen.")
            return
        df = pd.DataFrame(companies)

    if df.empty:
        render_empty_state("Keine Unternehmen mit Trades gefunden.")
        return

    # 2. KPIs
    kpis = [
        {"label": "Aktive Unternehmen", "value": str(len(df))},
        {"label": "Ø Trades pro Firma", "value": f"{df['trade_count'].mean():.1f}" if "trade_count" in df.columns else "-"},
    ]
    render_kpi_row(kpis)

    # 3. Filter (Suche)
    search = st.text_input("Unternehmen suchen (Name oder Symbol)", help="Filtert die untenstehende Tabelle.")
    summarize_filters("Aktive Filter", {"Suche": search.strip()})
    if search:
        df = df[
            (df["company_name"].str.contains(search, case=False, na=False)) |
            (df["current_symbol"].str.contains(search, case=False, na=False))
        ]
    unresolved_count = int(df.get("profile_status", pd.Series(dtype="object")).fillna("").astype(str).str.upper().ne("FETCHED").sum()) if "profile_status" in df.columns else 0
    if unresolved_count > 0:
        st.warning(
            f"Unvollständige Profile: {unresolved_count} Unternehmen ohne vollständiges API2-Profil. "
            "Diese Einträge bleiben sichtbar und können trotzdem analysiert werden."
        )

    # 4. Tabelle (Requirement 6.3)
    st.subheader("Unternehmens-Verzeichnis")
    st.caption("Sortierung: Unternehmen mit den meisten Trades zuerst. Zeilen sind einzeln auswählbar.")
    
    display_cols = ["current_symbol", "company_name", "sector", "industry", "market_cap", "trade_count", "last_trade_date"]
    
    # Sicherstellen dass Spalten da sind
    for col in display_cols:
        if col not in df.columns: df[col] = None

    event = st.dataframe(
        df[display_cols],
        column_config={
            "current_symbol": st.column_config.TextColumn("Symbol"),
            "company_name": st.column_config.TextColumn("Name"),
            "sector": st.column_config.TextColumn("Sektor"),
            "industry": st.column_config.TextColumn("Industrie"),
            "market_cap": st.column_config.NumberColumn("Marktkapitalisierung", format="$%d"),
            "trade_count": st.column_config.NumberColumn("Trades"),
            "last_trade_date": st.column_config.DateColumn("Letzter Trade", format="DD.MM.YY")
        },
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

    if event and event.get("selection") and event["selection"].get("rows"):
        selected_idx = event["selection"]["rows"][0]
        selected_company = df.iloc[selected_idx]
        
        if st.button(f"Unternehmens-Detail öffnen: {selected_company.get('company_name')}", type="primary", use_container_width=True):
            st.session_state["selected_company_symbol"] = selected_company.get("current_symbol")
            st.session_state["nav_target"] = "Unternehmens-Detail"
            st.rerun()
    else:
        st.info("Hinweis: Wählen Sie ein Unternehmen aus der Tabelle aus, um das Profil und die Historie anzuzeigen.")
