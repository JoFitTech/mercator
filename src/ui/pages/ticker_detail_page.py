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


def format_currency_compact(value: Any) -> str:
    """Formatiert Währungswerte kompakt (z.B. 1.25M, 842k)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    val = float(value)
    if abs(val) >= 1_000_000:
        return f"{val / 1_000_000:.2f}M"
    if abs(val) >= 1_000:
        return f"{val / 1_000:.1f}k"
    return f"{val:.2f}"


def render_ticker_detail_page(service: AnalysisService) -> None:
    """Rendert die Detailansicht für ein ausgewähltes Symbol."""
    st.title("Mercator")
    st.markdown("### Deep Dive Analysis")
    
    advanced_mode = st.session_state.get("advanced_mode", False)

    # Auswahl des Tickers
    try:
        all_symbols = sorted(list(set(service.trade_repo.fetch_all_symbols()) | set(service.company_repo.fetch_all_symbols())))
    except Exception:
        all_symbols = []

    if not all_symbols:
        st.info("Keine Daten verfügbar.")
        return

    selected_symbol = st.selectbox("Ticker wählen", all_symbols)
    if not selected_symbol:
        return

    result = service.get_ticker_detail(selected_symbol, accumulate=True)
    profile = result.company_profile

    def _safe_select_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        safe_df = frame.copy()
        for col in columns:
            if col not in safe_df.columns:
                safe_df[col] = pd.NA
        return safe_df[columns]

    # Layout mit Tabs für bessere Übersicht
    tab1, tab2, tab3 = st.tabs(["Overview & Trades", "Company Context", "Advanced Raw"])

    with tab1:
        # Summary Header
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Insider Trades", format_number(result.metrics.get("trade_count"), "{:,.0f}"))
        c2.metric("Ø Preis", format_number(result.metrics.get("avg_price")))
        c3.metric("Gesamtmenge", format_number(result.metrics.get("total_qty"), "{:,.0f}"))
        c4.metric("Marktkapitalisierung", format_mcap(profile.get('market_cap'), profile.get('currency', 'USD')))

        st.markdown("---")
        st.subheader("Insider Trades (Akkumuliert)")
        
        if result.rows:
            df_display = pd.DataFrame(result.rows)
            for col, default in {
                "is_accumulated": False,
                "accumulated_trade_count": 1,
                "accumulation_start_date": pd.NaT,
                "accumulation_end_date": pd.NaT,
                "transaction_date": pd.NaT,
            }.items():
                if col not in df_display.columns:
                    df_display[col] = default

            df_display["is_accumulated"] = df_display["is_accumulated"].fillna(False).astype(bool)
            df_display["accumulated_trade_count"] = pd.to_numeric(df_display["accumulated_trade_count"], errors="coerce").fillna(1)
            df_display["accumulation_start_date"] = pd.to_datetime(df_display["accumulation_start_date"], errors="coerce")
            df_display["accumulation_end_date"] = pd.to_datetime(df_display["accumulation_end_date"], errors="coerce")
            df_display["transaction_date"] = pd.to_datetime(df_display["transaction_date"], errors="coerce")

            # Spalten für die Detailansicht aufbereiten
            df_display["Range"] = df_display.apply(
                lambda r: (
                    f"{r['accumulation_start_date'].date()} bis {r['accumulation_end_date'].date()}"
                    if r["is_accumulated"] and pd.notna(r["accumulation_start_date"]) and pd.notna(r["accumulation_end_date"])
                    else (r["transaction_date"].date() if pd.notna(r["transaction_date"]) else "-")
                ),
                axis=1
            )
            df_display["Type"] = df_display.apply(
                lambda r: f"ACC x{r['accumulated_trade_count']}" if r['is_accumulated'] else "Single", 
                axis=1
            )

            # Wir nutzen st.dataframe mit NumberColumn für korrektes Sorting
            st.dataframe(
                _safe_select_columns(
                    df_display,
                    [
                        "Range",
                        "reporting_name",
                        "direction",
                        "accumulated_qty",
                        "accumulated_avg_price_weighted",
                        "accumulated_trade_value_estimated",
                        "score",
                        "score_class",
                        "gate_status",
                        "validation_status",
                        "Type",
                    ],
                ),
                column_config={
                    "Range": st.column_config.TextColumn("Zeitraum/Datum"),
                    "reporting_name": st.column_config.TextColumn("Insider"),
                    "direction": st.column_config.TextColumn("Richtung"),
                    "accumulated_qty": st.column_config.NumberColumn("Stückzahl", format="%d"),
                    "accumulated_avg_price_weighted": st.column_config.NumberColumn("Preis", format="$%.2f"),
                    "accumulated_trade_value_estimated": st.column_config.NumberColumn("Wert ($)", format="$%.2f"),
                    "score": st.column_config.NumberColumn("Score", format="%.2f"),
                    "score_class": st.column_config.TextColumn("Score Klasse"),
                    "gate_status": st.column_config.TextColumn("Gate"),
                    "validation_status": st.column_config.TextColumn("Validation"),
                    "Type": st.column_config.TextColumn("Typ")
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Einzeltrades bei Aggregaten zeigen (Progressive Disclosure)
            accumulated_trades = [r for r in result.rows if r.get("is_accumulated")]
            if accumulated_trades:
                with st.expander("Einzeltrades für Akkumulationen einsehen"):
                    raw_df = pd.DataFrame(result.raw_rows)
                    for acc in accumulated_trades:
                        group_id = acc.get("accumulation_group_id")
                        reporting_name = acc.get("reporting_name", "-")
                        direction = acc.get("direction", "UNKNOWN")
                        st.write(f"**Gruppe {group_id}** ({reporting_name}, {direction})")
                        # Matching über die neue accumulation_group_id
                        if "accumulation_group_id" not in raw_df.columns:
                            st.caption("Keine Gruppierungsdetails verfügbar.")
                            continue
                        group_trades = raw_df[raw_df["accumulation_group_id"] == group_id]
                        st.table(_safe_select_columns(group_trades, ["transaction_date", "qty", "price", "trade_value_estimated", "security_name"]))
        else:
            st.write("Keine Transaktionen gefunden.")

    with tab2:
        if profile:
            c1, c2 = st.columns([0.7, 0.3])
            with c1:
                st.subheader(f"{profile.get('company_name') or selected_symbol}")
                st.write(f"**Sektor:** {profile.get('sector') or '-'} | **Branche:** {profile.get('industry') or '-'}")
                st.write(f"**Land:** {profile.get('country') or '-'} | **Börse:** {profile.get('exchange_full_name') or '-'}")
                st.write(f"**ISIN:** {profile.get('isin') or '-'} | **CIK:** {profile.get('cik') or '-'}")
            with c2:
                if profile.get('website'):
                    st.link_button("Website besuchen", profile['website'], use_container_width=True)
                st.write(f"**CEO:** {profile.get('ceo') or '-'}")
                st.write(f"**Mitarbeiter:** {profile.get('full_time_employees') or '-'}")

            st.markdown("**Beschreibung:**")
            st.write(profile.get('description') or 'Keine Beschreibung verfügbar.')
        else:
            st.warning("Kein Firmenprofil gefunden.")

    with tab3:
        st.subheader("Technische Metadaten")
        if result.raw_rows:
            st.json(result.raw_rows[:5]) # Nur die ersten 5 zeigen
            st.download_button("Alle Rohdaten laden (JSON)", data=str(result.raw_rows), file_name=f"{selected_symbol}_raw.json")
        else:
            st.write("Keine Rohdaten verfügbar.")
