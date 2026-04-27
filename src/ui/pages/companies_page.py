"""Unternehmen-Seite mit Fokus auf aktive Firmen (Requirement 6)."""

from __future__ import annotations
from datetime import date, timedelta
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
PAGE_SIZES = [50, 100, 200]


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
        return "—"
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _clamp_page(current_page: int, total_rows: int, page_size: int) -> tuple[int, int]:
    total_pages = max(1, (int(total_rows) + int(page_size) - 1) // int(page_size))
    return min(max(1, int(current_page)), total_pages), total_pages


def render_companies_page(repository: CompanyMySqlRepository | None, db_status: DatabaseStatus | None = None) -> None:
    """Rendert die Unternehmens-Übersicht."""
    render_page_header("Unternehmen", "Unternehmen mit Insider-Aktivitaet und Profilstatus.")
    if repository is None:
        st.warning("Unternehmensdaten sind derzeit nicht verfügbar, da MySQL nicht erreichbar ist.")
        return

    # 1. Filter (Suche)
    search = st.text_input(
        "Unternehmen suchen (Name oder Symbol)",
        key="companies_search_term",
        help="Filtert die untenstehende Tabelle.",
    )
    search_term = search.strip()
    feedback = st.session_state.pop("companies_feedback", None)
    if feedback:
        st.success(str(feedback))
    p1, p2 = st.columns([1, 1])
    page_size = p1.selectbox("Seitengröße", options=PAGE_SIZES, index=1, key="companies_page_size")
    current_page = max(1, int(p2.number_input("Seite", min_value=1, value=1, step=1, key="companies_current_page")))
    summarize_filters("Aktive Filter", {"Suche": search_term})

    # 2. Serverseitig paginierte Daten laden
    with st.spinner("Lade Unternehmen..."):
        if hasattr(repository, "count_active_companies") and hasattr(repository, "list_active_companies_page"):
            total_companies, count_error = safe_service_call(
                lambda: repository.count_active_companies(search_term=search_term or None),
                context_label="Unternehmensdaten",
                fallback=0,
            )
            valid_page, total_pages = _clamp_page(current_page, int(total_companies), int(page_size))
            if valid_page != current_page:
                st.session_state["companies_current_page"] = int(valid_page)
                current_page = int(valid_page)
            offset = (current_page - 1) * int(page_size)
            companies, error = safe_service_call(
                lambda: repository.list_active_companies_page(limit=int(page_size), offset=offset, search_term=search_term or None),
                context_label="Unternehmensdaten",
                fallback=[],
            )
        else:
            # Rückwärtskompatibler Fallback für ältere Repos und bestehende UI-Tests.
            companies_all, error = safe_service_call(
                lambda: repository.list_active_companies(limit=1000),
                context_label="Unternehmensdaten",
                fallback=[],
            )
            count_error = None
            if search_term:
                companies_all = [
                    row for row in companies_all
                    if search_term.lower() in str(row.get("company_name") or "").lower()
                    or search_term.lower() in str(row.get("current_symbol") or "").lower()
                ]
            total_companies = len(companies_all)
            valid_page, total_pages = _clamp_page(current_page, int(total_companies), int(page_size))
            if valid_page != current_page:
                st.session_state["companies_current_page"] = int(valid_page)
                current_page = int(valid_page)
            offset = (current_page - 1) * int(page_size)
            companies = companies_all[offset: offset + int(page_size)]
        if error is not None or count_error is not None:
            st.warning("Unternehmen konnten nicht geladen werden. Bitte später erneut versuchen.")
            return
        df = pd.DataFrame(companies)

    if df.empty and search_term:
        render_empty_state(f"Keine Unternehmen für den Suchbegriff „{search_term}“ gefunden.")
        if st.button("Suche zurücksetzen", key="companies_reset_search", use_container_width=True):
            st.session_state["companies_search_term"] = ""
            st.session_state["companies_current_page"] = 1
            st.session_state["companies_feedback"] = "Suche wurde zurückgesetzt."
            st.rerun()
        return
    if df.empty:
        render_empty_state("Keine Unternehmen mit Trades gefunden.")
        return

    st.caption(f"Seite {current_page} von {total_pages} · Gesamt {total_companies} Unternehmen")

    # 3. KPIs
    kpis = [
        {"label": "Aktive Unternehmen", "value": str(total_companies)},
        {"label": "Ø Trades pro Firma", "value": f"{df['trade_count'].mean():.1f}" if "trade_count" in df.columns else "-"},
    ]
    render_kpi_row(kpis)

    unresolved_count = int(df.get("profile_status", pd.Series(dtype="object")).fillna("").astype(str).str.upper().ne("FETCHED").sum()) if "profile_status" in df.columns else 0
    if unresolved_count > 0:
        st.caption(f"Hinweis: Unvollstaendige Profile ({unresolved_count})")

    # 4. Tabelle (Requirement 6.3)
    st.subheader("Unternehmens-Verzeichnis")
    st.caption(
        "Sortierung: standardmäßig nach Trade-Anzahl (absteigend). "
        "Sie können zusätzlich über Spaltenüberschriften sortieren."
    )
    
    display_cols = ["current_symbol", "company_name", "sector", "industry", "market_cap", "trade_count", "profile_status", "last_trade_date"]

    # Sicherstellen dass Spalten da sind
    for col in display_cols:
        if col not in df.columns: df[col] = None

    work_df = df[display_cols].copy()
    work_df["__row_id"] = range(len(work_df))
    work_df["current_symbol"] = work_df["current_symbol"].apply(lambda v: _ui_text(v, fallback="–"))
    work_df["company_name"] = work_df.apply(_company_display_name, axis=1)
    work_df["sector"] = work_df["sector"].apply(lambda v: _ui_text(v, fallback="—"))
    work_df["industry"] = work_df["industry"].apply(lambda v: _ui_text(v, fallback="—"))
    work_df["profile_status"] = work_df["profile_status"].apply(lambda v: _ui_text(v, fallback="—")).str.upper()
    work_df["market_cap"] = work_df["market_cap"].apply(_format_market_cap)
    work_df["trade_count"] = pd.to_numeric(work_df["trade_count"], errors="coerce").fillna(0).astype(int)
    work_df["last_trade_date"] = pd.to_datetime(work_df["last_trade_date"], errors="coerce").dt.strftime("%d.%m.%Y").fillna("—")
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
            "profile_status": st.column_config.TextColumn("Profile Status"),
            "last_trade_date": st.column_config.TextColumn("Letzter Trade"),
        },
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

    selected_idx = get_single_selected_row_index(event, len(display_df))
    if selected_idx is not None:
        try:
            selected_company = source_df.iloc[selected_idx]
        except (IndexError, KeyError):
            st.error("Ausgewählte Zeile ist ungültig. Bitte erneut auswählen.")
            return

        company_label = _company_display_name(selected_company)
        symbol_value = _ui_text(selected_company.get("current_symbol"), fallback="")
        can_navigate = bool(symbol_value)

        with st.container(border=True):
            st.markdown(f"**Ausgewählt:** {company_label}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button(
                    "Unternehmensdetails oeffnen",
                    type="primary",
                    use_container_width=True,
                    disabled=not can_navigate,
                    key=f"companies_open_detail_{selected_idx}",
                    help="Navigation benoetigt ein gueltiges Symbol." if not can_navigate else None,
                ):
                    st.session_state["selected_company_symbol"] = symbol_value
                    st.session_state["nav_target"] = "Unternehmens-Detail"
                    st.rerun()
            with c2:
                if st.button(
                    "Trades anzeigen",
                    use_container_width=True,
                    disabled=not can_navigate,
                    key=f"companies_open_trades_{selected_idx}",
                ):
                    st.session_state["trades_filters"] = {
                        "symbol": symbol_value,
                        "reporting_name": "",
                        "direction": "Alle",
                        "gate_status": "Alle",
                        "validation_status": "Alle",
                        "date_range": (date.today() - timedelta(days=90), date.today()),
                        "min_score": 0,
                        "min_value": 0,
                        "accumulate_trades": True,
                        "show_single_trades": False,
                        "accumulation_limit": 2000,
                    }
                    st.session_state["nav_target"] = "Trades"
                    st.rerun()
    else:
        st.info("Bitte eine Zeile markieren, damit der Detail-Button aktiv wird.")
