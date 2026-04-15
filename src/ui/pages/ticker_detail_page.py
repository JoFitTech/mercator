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
        all_symbols = service.list_ticker_options()
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

    status = result.metrics.get("overall_status", "UNKNOWN")
    status_map = {
        "PASS": {"color": "green", "label": "PASS"},
        "HOLD": {"color": "orange", "label": "HOLD"},
        "FAIL": {"color": "red", "label": "FAIL"},
    }
    s_info = status_map.get(status, {"color": "gray", "label": status})

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Trades", format_number(result.metrics.get("trade_count"), "{:,.0f}"))
    m2.metric("Ø Preis", format_number(result.metrics.get("avg_price"), "${:,.2f}"))
    m3.metric("Status", s_info["label"])
    m4.metric("Marktkapitalisierung", format_mcap(profile.get("market_cap"), profile.get("currency", "USD")))
    m5.metric("Profilquelle", result.note)

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
                        "accumulated_trade_value_estimated",
                        "score",
                        "score_class",
                        "gate_status",
                        "accumulated_trade_count",
                        "accumulated_qty",
                        "accumulated_avg_price_weighted",
                        "validation_status",
                    ],
                ),
                column_config={
                    "Zeitraum": st.column_config.TextColumn("Zeitraum", width="medium"),
                    "reporting_name": st.column_config.TextColumn("Insider", width="medium"),
                    "direction": st.column_config.TextColumn("Richtung", width="small"),
                    "accumulated_trade_value_estimated": st.column_config.NumberColumn("Trade Value", format="$%.2f", width="large"),
                    "score": st.column_config.NumberColumn("Score", format="%.2f", width="small"),
                    "score_class": st.column_config.TextColumn("Klasse", width="small"),
                    "gate_status": st.column_config.TextColumn("Gate", width="small"),
                    "accumulated_trade_count": st.column_config.NumberColumn("#Trades", format="%d", width="small"),
                    "accumulated_qty": st.column_config.NumberColumn("Stück", format="%d", width="medium"),
                    "accumulated_avg_price_weighted": st.column_config.NumberColumn("Ø Preis", format="$%.2f", width="medium"),
                    "validation_status": st.column_config.TextColumn("Validation", width="small"),
                },
                use_container_width=True,
                hide_index=True,
                height=520,
            )

    with tab2:
        if not result.metrics.get("can_enrich"):
            st.info("### Unternehmensprofil nicht verfügbar")
            st.write("Gemäß den Fachregeln werden für Symbole mit Status **FAIL** keine erweiterten Unternehmensdaten geladen oder angezeigt. Dies dient der Datenökonomie und Fokus auf valide Kandidaten.")
        elif not profile:
            st.warning("Unternehmensprofil derzeit nicht verfügbar")
        else:
            def safe_value(value: Any) -> str:
                if value is None or str(value).strip() == "" or str(value).lower() == "none":
                    return "Nicht verfügbar"
                return str(value)

            c1, c2 = st.columns([0.65, 0.35])
            with c1:
                st.subheader(safe_value(profile.get("company_name") or selected_symbol))
                st.write(f"**Sektor:** {safe_value(profile.get('sector'))}")
                st.write(f"**Branche:** {safe_value(profile.get('industry'))}")
                st.write(f"**Land:** {safe_value(profile.get('country'))}")
                st.write(f"**Börse:** {safe_value(profile.get('exchange_full_name'))}")
            with c2:
                st.write(f"**ISIN:** {safe_value(profile.get('isin'))}")
                st.write(f"**CIK:** {safe_value(profile.get('cik'))}")
                st.write(f"**CEO:** {safe_value(profile.get('ceo'))}")
                st.write(f"**Mitarbeiter:** {safe_value(profile.get('full_time_employees'))}")
                if profile.get("website"):
                    st.link_button("Unternehmenswebsite", profile["website"], use_container_width=True)

            st.markdown("**Beschreibung**")
            st.write(safe_value(profile.get("description")))

        gate_df = pd.DataFrame(result.rows)
        if not gate_df.empty and "gate_status" in gate_df.columns:
            st.markdown("**Gate-Ergebnis**")
            gate_counts = gate_df["gate_status"].fillna("UNKNOWN").astype(str).str.upper().value_counts()
            st.write(
                f"PASS: {int(gate_counts.get('PASS', 0))} · HOLD/PENDING: {int(gate_counts.get('PENDING', 0))} · FAIL: {int(gate_counts.get('FAIL', 0))}"
            )
            failed = gate_df[gate_df["gate_status"].fillna("").astype(str).str.upper() == "FAIL"]
            if not failed.empty:
                st.dataframe(_safe_select_columns(failed, ["transaction_date", "reporting_name", "gate_reason"]), hide_index=True)

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
