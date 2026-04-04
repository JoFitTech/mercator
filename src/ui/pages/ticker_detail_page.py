"""Ticker-Detailseite mit Profil, Trades und Kennzahlen."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from typing import Any

from src.services.analysis_service import AnalysisService


def format_mcap(value: Any, currency: str = "USD") -> str:
    """Sichere Formatierung der Marktkapitalisierung."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return f"- {currency}"
    try:
        return f"{float(value):,.0f} {currency}"
    except (ValueError, TypeError):
        return f"- {currency}"


def format_number(value: Any, format_spec: str = "{:,.2f}", na_rep: str = "-") -> str:
    """Sicherer Formatter für Kennzahlen in der UI."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return na_rep
    try:
        return format_spec.format(float(value))
    except (ValueError, TypeError):
        return na_rep


def render_ticker_detail_page(service: AnalysisService) -> None:
    """Rendert die Detailansicht für ein ausgewähltes Symbol."""
    st.title("Mercator")
    st.markdown("### Ticker-Detailansicht")
    st.caption(
        "Detaillierte Sicht auf ausgewählte Unternehmen, Transaktionen und vorbereitete Analysekennzahlen."
    )

    advanced_mode = st.session_state.get("advanced_mode", False)

    # Company-Keys aus Trades und Profilen kombinieren für robuste Auswahl
    try:
        trade_company_keys = set(service.trade_repo.fetch_all_symbols())
        profile_company_keys = set(service.company_repo.fetch_all_symbols())
        all_symbols = sorted(list(trade_company_keys | profile_company_keys))
    except Exception:
        all_symbols = sorted(list(service.company_repo.fetch_all_symbols()))

    if not all_symbols:
        st.info("Es sind aktuell noch keine verarbeiteten Daten verfügbar. Lade zunächst einen Datensatz.")
        return

    selected_symbol = st.selectbox("Unternehmen auswählen", all_symbols)

    if not selected_symbol:
        return

    result = service.get_ticker_detail(selected_symbol)
    profile = result.company_profile

    st.markdown("---")
    
    # Kopfbereich mit Firmenkontext
    if profile:
        c1, c2 = st.columns([0.7, 0.3])
        with c1:
            st.subheader(f"{profile.get('company_name') or selected_symbol} ({profile.get('current_symbol') or '-'})")
            st.write(f"**Sektor:** {profile.get('sector') or '-'} | **Branche:** {profile.get('industry') or '-'}")
            st.write(f"**Land:** {profile.get('country') or '-'} | **Börse:** {profile.get('exchange_full_name') or '-'}")
        with c2:
            if profile.get('website'):
                st.link_button("Website besuchen", profile['website'], use_container_width=True)
            st.metric("Marktkapitalisierung", format_mcap(profile.get('market_cap'), profile.get('currency', 'USD')))

        with st.expander("Unternehmensbeschreibung", expanded=False):
            st.write(profile.get('description') or 'Keine Beschreibung verfügbar.')
            if advanced_mode:
                st.markdown("**Management:**")
                st.write(f"CEO: {profile.get('ceo') or '-'}")
                st.write(f"Mitarbeiter: {profile.get('full_time_employees') or '-'}")
    else:
        st.warning(f"Kein Firmenprofil für {selected_symbol} gefunden. Eventuell wurde noch kein Gate-PASS erreicht.")

    st.markdown("---")
    st.subheader("Insider-Analyse")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Anzahl Trades", format_number(result.metrics.get("trade_count"), "{:,.0f}"))
    m2.metric("Ø Preis", format_number(result.metrics.get("avg_price")))
    m3.metric("Gesamtmenge (Qty)", format_number(result.metrics.get("total_qty"), "{:,.0f}"))
    
    # Ein fiktiver Score als Platzhalter
    m4.metric("Analyse-Score", "Vorbereitet", help="Platzhalter für zukünftige Score-Erweiterung.")

    if advanced_mode:
        st.info(result.note)

    st.subheader("Letzte Transaktionen")
    if result.rows:
        df_trades = pd.DataFrame(result.rows)
        # Relevante Spalten für Detailansicht
        cols = ["transaction_date", "reporting_name", "transaction_type", "qty", "price", "trade_value_estimated", "gate_status"]
        existing = [c for c in cols if c in df_trades.columns]
        st.dataframe(
            df_trades[existing].style.format({
                "price": "{:,.2f}",
                "qty": "{:,.0f}",
                "trade_value_estimated": "{:,.2f}"
            }, na_rep="-"),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.write("Keine Transaktionen für dieses Symbol gefunden.")
