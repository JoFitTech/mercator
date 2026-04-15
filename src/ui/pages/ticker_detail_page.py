"""Ticker-Detailseite mit Profil, Trades und Kennzahlen."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.services.analysis_service import AnalysisService


def format_mcap(value: Any, currency: str = "USD") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return f"- {currency}"
    try:
        return f"{float(value):,.0f} {currency}"
    except (ValueError, TypeError):
        return f"- {currency}"


def format_number(value: Any, format_spec: str = "{:,.2f}", na_rep: str = "-") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return na_rep
    try:
        return format_spec.format(float(value))
    except (ValueError, TypeError):
        return na_rep


def _safe_select_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    safe_df = frame.copy()
    for col in columns:
        if col not in safe_df.columns:
            safe_df[col] = pd.NA
    return safe_df[columns]


def render_ticker_detail_page(service: AnalysisService) -> None:
    """Rendert die Detailansicht für ein ausgewähltes Symbol."""
    st.title("Detailansicht")
    st.caption("Kontext pro Unternehmen: Trade-Historie, Qualitätsindikatoren und Profildaten für den finalen Entscheid.")

    try:
        all_symbols = sorted(list(set(service.trade_repo.fetch_all_symbols()) | set(service.company_repo.fetch_all_symbols())))
    except Exception:
        all_symbols = []

    if not all_symbols:
        st.info("Keine Daten verfügbar.")
        return

    default_index = 0
    if st.session_state.get("selected_ticker") in all_symbols:
        default_index = all_symbols.index(st.session_state["selected_ticker"])

    selected_symbol = st.selectbox("Ticker", all_symbols, index=default_index)
    if not selected_symbol:
        return

    result = service.get_ticker_detail(selected_symbol, accumulate=True)
    profile = result.company_profile

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Trades", format_number(result.metrics.get("trade_count"), "{:,.0f}"))
    m2.metric("Ø Preis", format_number(result.metrics.get("avg_price"), "${:,.2f}"))
    m3.metric("Gesamtmenge", format_number(result.metrics.get("total_qty"), "{:,.0f}"))
    m4.metric("Marktkapitalisierung", format_mcap(profile.get("market_cap"), profile.get("currency", "USD")))

    tab1, tab2, tab3 = st.tabs(["Trades", "Company Context", "Raw / Audit"])

    with tab1:
        st.subheader("Insider Trades (akkumuliert)")

        if not result.rows:
            st.info(f"Keine Transaktionen für {selected_symbol} gefunden.")
            if result.note:
                st.caption(f"Hinweis: {result.note}")
        else:
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

            df_display["Zeitraum"] = df_display.apply(
                lambda r: (
                    f"{r['accumulation_start_date'].date()} bis {r['accumulation_end_date'].date()}"
                    if r["is_accumulated"] and pd.notna(r["accumulation_start_date"]) and pd.notna(r["accumulation_end_date"])
                    else (r["transaction_date"].date() if pd.notna(r["transaction_date"]) else "-")
                ),
                axis=1,
            )

            st.dataframe(
                _safe_select_columns(
                    df_display,
                    [
                        "Zeitraum",
                        "reporting_name",
                        "direction",
                        "accumulated_trade_count",
                        "accumulated_qty",
                        "accumulated_avg_price_weighted",
                        "accumulated_trade_value_estimated",
                        "score",
                        "score_class",
                        "gate_status",
                        "validation_status",
                    ],
                ),
                column_config={
                    "Zeitraum": st.column_config.TextColumn("Zeitraum", width="medium"),
                    "reporting_name": st.column_config.TextColumn("Insider", width="medium"),
                    "direction": st.column_config.TextColumn("Richtung", width="small"),
                    "accumulated_trade_count": st.column_config.NumberColumn("#Trades", format="%d", width="small"),
                    "accumulated_qty": st.column_config.NumberColumn("Stück", format="%d"),
                    "accumulated_avg_price_weighted": st.column_config.NumberColumn("Ø Preis", format="$%.2f"),
                    "accumulated_trade_value_estimated": st.column_config.NumberColumn("Trade Value", format="$%.2f", width="medium"),
                    "score": st.column_config.NumberColumn("Score", format="%.2f", width="small"),
                    "score_class": st.column_config.TextColumn("Klasse", width="small"),
                    "gate_status": st.column_config.TextColumn("Gate", width="small"),
                    "validation_status": st.column_config.TextColumn("Validation", width="small"),
                },
                use_container_width=True,
                hide_index=True,
                height=520,
            )

    with tab2:
        if not profile:
            st.warning("Kein Firmenprofil gefunden.")
        else:
            c1, c2 = st.columns([0.65, 0.35])
            with c1:
                st.subheader(f"{profile.get('company_name') or selected_symbol}")
                st.write(f"**Sektor:** {profile.get('sector') or '-'}")
                st.write(f"**Branche:** {profile.get('industry') or '-'}")
                st.write(f"**Land:** {profile.get('country') or '-'}")
                st.write(f"**Börse:** {profile.get('exchange_full_name') or '-'}")
            with c2:
                st.write(f"**ISIN:** {profile.get('isin') or '-'}")
                st.write(f"**CIK:** {profile.get('cik') or '-'}")
                st.write(f"**CEO:** {profile.get('ceo') or '-'}")
                st.write(f"**Mitarbeiter:** {profile.get('full_time_employees') or '-'}")
                if profile.get("website"):
                    st.link_button("Unternehmenswebsite", profile["website"], use_container_width=True)

            st.markdown("**Beschreibung**")
            st.write(profile.get("description") or "Keine Beschreibung verfügbar.")

    with tab3:
        st.subheader("Technische Metadaten")
        if result.raw_rows:
            st.json(result.raw_rows[:5])
            st.download_button(
                "Rohdaten als JSON herunterladen",
                data=str(result.raw_rows),
                file_name=f"{selected_symbol}_raw.json",
            )
        else:
            st.info("Keine Rohdaten verfügbar.")
