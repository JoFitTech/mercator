"""Dashboard-Seite mit KPIs und fokussierten Überblicksvisualisierungen."""

from __future__ import annotations

import streamlit as st

from src.config.settings import AppSettings
from src.preprocessing.gate_evaluator import GATE_FAIL, GATE_PASS, GATE_PENDING
from src.services.app_settings_service import AppSettingsService, RuntimeSettings
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService


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


def render_dashboard_page(
    service: DashboardService | None,
    import_service: ImportService | None = None,
    settings: AppSettings | None = None,
    runtime_settings_service: AppSettingsService | None = None,
) -> None:
    """Rendert KPI-Karten und fokussierte Diagramme für den Gesamtüberblick."""
    st.title("Overview")
    st.caption("Systemzustand, Datenabdeckung und Marktmuster als schnelle Entscheidungsbasis für den Explorer.")

    if settings is not None and settings.review_mode:
        st.warning("Review Instance - Read Only (Import und Löschaktionen sind deaktiviert).")

    advanced_mode = st.session_state.get("advanced_mode", False)
    runtime_settings = runtime_settings_service.load() if runtime_settings_service else None

    if runtime_settings is not None and runtime_settings_service is not None:
        _render_runtime_preferences(runtime_settings_service, runtime_settings)

    if settings is not None:
        with st.expander("Import", expanded=advanced_mode):
            c1, c2 = st.columns(2)
            page = c1.number_input("Feed-Seite", min_value=0, step=1, value=settings.fmp.default_feed_page)
            limit = c2.number_input("Feed-Limit", min_value=1, max_value=1000, step=10, value=settings.fmp.default_feed_limit)

            status_options = [GATE_PASS, GATE_PENDING, GATE_FAIL]
            selected_statuses = st.multiselect(
                "Gate-Status für Profil-Anreicherung",
                options=status_options,
                default=list(runtime_settings.profile_gate_filter_statuses if runtime_settings else settings.fmp.profile_gate_filter_statuses),
            )

            import_blocked = settings.review_mode or settings.disable_import
            if import_blocked:
                st.info("Import ist im Review Mode deaktiviert.")

            if st.button("Datenimport starten", type="primary", use_container_width=True, disabled=import_blocked):
                if import_service is None:
                    st.warning("Import-Service nicht verfügbar. Rohdatenspeicherung ist derzeit deaktiviert.")
                    error_detail = st.session_state.get("import_service_error")
                    if error_detail:
                        st.caption(f"Technischer Hinweis: {error_detail}")
                else:
                    try:
                        with st.spinner("Import läuft..."):
                            summary = import_service.run_hourly_import(
                                page=int(page),
                                limit=int(limit),
                                profile_fetch_statuses=tuple(selected_statuses),
                            )
                        st.success(
                            "Import abgeschlossen: %s Rohdatensätze, %s Profile geladen."
                            % (summary.fetched_feed_records, summary.fetched_profiles)
                        )
                    except RuntimeError as exc:
                        st.warning(str(exc))

    if service is None:
        st.warning("MySQL nicht erreichbar. Analysefunktionen sind eingeschränkt.")
        if import_service is None:
            st.info("Keine Datenverarbeitung verfügbar. Prüfe Datenbankverbindungen.")
        return

    payload = service.build_dashboard_payload()
    if payload["clean_records"] == 0:
        st.warning(EMPTY_DATA_MESSAGE)
        return

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Rohdaten (Mongo)", f"{payload['raw_records']:,}")
    k2.metric("Bereinigte Trades", f"{payload['clean_records']:,}")
    k3.metric("Profile", f"{payload['company_profiles']:,}")
    k4.metric("Gate PASS", f"{payload.get('gate_pass_records', 0):,}")

    left, right = st.columns([0.64, 0.36])

    with left:
        st.subheader("Trade Value über Zeit")
        if not payload["buy_sell_volume"].empty:
            chart_df = payload["buy_sell_volume"].set_index("event_date")
            st.area_chart(chart_df, height=320)
        else:
            st.info("Keine Zeitreihendaten verfügbar.")

        st.subheader("Sektorverteilung")
        if not payload["sector_distribution"].empty:
            sector_df = payload["sector_distribution"].sort_values("count", ascending=False).head(12)
            st.bar_chart(sector_df.set_index("sector"), horizontal=True, height=320)
        else:
            st.info("Keine Sektordaten verfügbar.")

    with right:
        st.subheader("Richtungsbalance")
        if not payload["trades"].empty:
            counts = payload["trades"]["direction"].value_counts()
            buy_c = int(counts.get("BUY", 0))
            sell_c = int(counts.get("SELL", 0))
            total = buy_c + sell_c
            ratio = buy_c / total if total else 0
            st.metric("BUY", f"{buy_c:,}")
            st.metric("SELL", f"{sell_c:,}")
            st.progress(ratio, text=f"BUY-Quote {ratio:.0%}")
        else:
            st.info("Keine Richtungsdaten verfügbar.")

        st.subheader("Top-Kandidaten (Vorschau)")
        trades_df = payload["trades"].copy()
        if not trades_df.empty:
            score_series = trades_df["score"] if "score" in trades_df.columns else 0
            value_series = trades_df["trade_value_estimated"] if "trade_value_estimated" in trades_df.columns else 0
            trades_df = trades_df.assign(
                _score=score_series,
                _value=value_series,
            ).sort_values(by=["_score", "_value"], ascending=[False, False])

            preview_cols = [
                "symbol_at_trade",
                "reporting_name",
                "direction",
                "score",
                "score_class",
                "trade_value_estimated",
                "gate_status",
                "validation_status",
            ]
            for col in preview_cols:
                if col not in trades_df.columns:
                    trades_df[col] = None
            st.dataframe(
                trades_df.head(8)[preview_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "symbol_at_trade": st.column_config.TextColumn("Ticker", width="small"),
                    "reporting_name": st.column_config.TextColumn("Insider", width="medium"),
                    "direction": st.column_config.TextColumn("Richtung", width="small"),
                    "score": st.column_config.NumberColumn("Score", format="%.2f", width="small"),
                    "score_class": st.column_config.TextColumn("Klasse", width="small"),
                    "trade_value_estimated": st.column_config.NumberColumn("Trade Value", format="$%.2f", width="medium"),
                    "gate_status": st.column_config.TextColumn("Gate", width="small"),
                    "validation_status": st.column_config.TextColumn("Validation", width="small"),
                },
                height=310,
            )
        else:
            st.info("Keine Kandidaten verfügbar.")

    if advanced_mode and not payload["timeline_distribution"].empty:
        st.subheader("Import-Historie (Advanced)")
        st.line_chart(payload["timeline_distribution"].set_index("e_date"))
