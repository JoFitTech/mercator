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
from src.ui.components.tables import get_single_selected_row_index


def _is_missing_ui_value(value: object) -> bool:
    if value is None:
        return True
    if pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "none", "n/a"}


def _ui_text(value: object, fallback: str = "Nicht verfügbar") -> str:
    return fallback if _is_missing_ui_value(value) else str(value).strip()


def _company_display_name(row: pd.Series) -> str:
    company_name = _ui_text(row.get("company_name"), fallback="")
    if company_name:
        return company_name
    symbol = _ui_text(row.get("current_symbol"), fallback="")
    if symbol:
        return symbol
    return "Unbekanntes Unternehmen"


def _format_market_cap(value: object) -> str:
    if _is_missing_ui_value(value):
        return "Nicht verfügbar"
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "Nicht verfügbar"


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
    search = st.text_input(
        "Unternehmen suchen (Name oder Symbol)",
        key="companies_search_term",
        help="Filtert die untenstehende Tabelle.",
    )
    search_term = search.strip()
    summarize_filters("Aktive Filter", {"Suche": search_term})
    if search_term:
        df = df[
            (df["company_name"].str.contains(search_term, case=False, na=False)) |
            (df["current_symbol"].str.contains(search_term, case=False, na=False))
        ]
    if df.empty and search_term:
        render_empty_state(f"Keine Unternehmen für den Suchbegriff „{search_term}“ gefunden.")
        if st.button("Suche zurücksetzen", key="companies_reset_search", use_container_width=True):
            st.session_state["companies_search_term"] = ""
            st.rerun()
        return
    unresolved_count = int(df.get("profile_status", pd.Series(dtype="object")).fillna("").astype(str).str.upper().ne("FETCHED").sum()) if "profile_status" in df.columns else 0
    if unresolved_count > 0:
        st.warning(
            f"Unvollständige Profile: {unresolved_count} Unternehmen ohne vollständiges API2-Profil. "
            "Diese Einträge bleiben sichtbar und können trotzdem analysiert werden."
        )

    # 4. Tabelle (Requirement 6.3)
    st.subheader("Unternehmens-Verzeichnis")
    st.caption(
        "Sortierung: standardmäßig nach Trade-Anzahl (absteigend). "
        "Sie können zusätzlich über Spaltenüberschriften sortieren."
    )
    
    display_cols = ["current_symbol", "company_name", "sector", "industry", "market_cap", "trade_count", "last_trade_date"]
    
    # Sicherstellen dass Spalten da sind
    for col in display_cols:
        if col not in df.columns: df[col] = None

    work_df = df[display_cols].copy()
    work_df["__row_id"] = range(len(work_df))
    work_df["current_symbol"] = work_df["current_symbol"].apply(lambda v: _ui_text(v, fallback="–"))
    work_df["company_name"] = work_df.apply(_company_display_name, axis=1)
    work_df["sector"] = work_df["sector"].apply(lambda v: _ui_text(v, fallback="Nicht verfügbar"))
    work_df["industry"] = work_df["industry"].apply(lambda v: _ui_text(v, fallback="Nicht verfügbar"))
    work_df["market_cap"] = work_df["market_cap"].apply(_format_market_cap)
    work_df["trade_count"] = pd.to_numeric(work_df["trade_count"], errors="coerce").fillna(0).astype(int)
    work_df["last_trade_date"] = pd.to_datetime(work_df["last_trade_date"], errors="coerce").dt.strftime("%d.%m.%Y").fillna("Nicht verfügbar")
    work_df = work_df.sort_values("trade_count", ascending=False).reset_index(drop=True)
    source_df = df.reset_index(drop=True).iloc[work_df["__row_id"]].reset_index(drop=True)
    display_df = work_df.drop(columns=["__row_id"])

    event = st.dataframe(
        display_df,
        column_config={
            "current_symbol": st.column_config.TextColumn("Symbol"),
            "company_name": st.column_config.TextColumn("Name"),
            "sector": st.column_config.TextColumn("Sektor"),
            "industry": st.column_config.TextColumn("Industrie"),
            "market_cap": st.column_config.TextColumn("Marktkapitalisierung"),
            "trade_count": st.column_config.NumberColumn("Trades"),
            "last_trade_date": st.column_config.TextColumn("Letzter Trade"),
        },
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

    selected_idx = get_single_selected_row_index(event, len(display_df))
    if selected_idx is not None:
        selected_company = source_df.iloc[selected_idx]
        company_label = _company_display_name(selected_company)
        symbol_value = _ui_text(selected_company.get("current_symbol"), fallback="")
        can_navigate = bool(symbol_value)

        with st.container(border=True):
            st.markdown(f"**Ausgewählt:** {company_label}")
            if st.button(
                f"Unternehmens-Detail öffnen: {company_label}",
                type="primary",
                use_container_width=True,
                disabled=not can_navigate,
                key=f"companies_open_detail_{selected_idx}",
                help="Navigation benötigt ein gültiges Symbol." if not can_navigate else None,
            ):
                st.session_state["selected_company_symbol"] = symbol_value
                st.session_state["nav_target"] = "Unternehmens-Detail"
                st.rerun()
    else:
        st.info("Bitte eine Zeile markieren, damit der Detail-Button aktiv wird.")
