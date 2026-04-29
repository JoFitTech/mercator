from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from src.config.settings import AppSettings
from src.db.repositories.trade_republic_universe_repository import TradeRepublicUniverseRepository
from src.services.trade_republic_universe_service import TradeRepublicUniverseIngestionService


def _fmt_dt(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    text = str(value or "").strip()
    return text or "-"


def render_trade_republic_universe_tab(
    settings: AppSettings,
    mysql_client,
    admin_service,
) -> None:
    st.subheader("Trade Republic Universum")
    if mysql_client is None:
        st.warning("MySQL nicht verfügbar. TR-Referenzdaten können nicht angezeigt werden.")
        return

    repo = TradeRepublicUniverseRepository(mysql_client)
    ingestion = TradeRepublicUniverseIngestionService(settings=settings, mysql_client=mysql_client)

    meta = repo.get_meta(settings.trade_republic_universe_url)
    total = int(meta.get("instrument_count", 0) or 0)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Instrumente", f"{total:,}")
    c2.metric("Letzter Refresh", _fmt_dt(meta.get("source_last_refreshed_at")))
    c3.metric("Quelle", str(meta.get("source_url") or settings.trade_republic_universe_source_mode))
    c4.metric("Letzter Fehler", "Ja" if meta.get("last_error") else "Nein")

    a1, a2 = st.columns(2)
    if a1.button("Trade-Republic-Universum aktualisieren", type="primary", use_container_width=True):
        with st.spinner("Aktualisiere TR-Universum..."):
            summary = ingestion.refresh(force=True)
        if summary.status == "refreshed":
            st.success(f"Aktualisiert: {summary.inserted_rows} Instrumente ({summary.source_type}).")
        else:
            st.error(summary.error or f"Aktualisierung fehlgeschlagen ({summary.status}).")
        st.rerun()

    if a2.button("Lokale CSV importieren", use_container_width=True):
        with st.spinner("Importiere lokale CSV..."):
            summary = ingestion.refresh_from_local_csv()
        if summary.status == "refreshed":
            st.success(f"Lokale CSV importiert: {summary.inserted_rows} Instrumente.")
        else:
            st.error(summary.error or f"CSV-Import fehlgeschlagen ({summary.status}).")
        st.rerun()

    st.markdown("---")
    q_col, ac_col, co_col, p_col = st.columns([2, 1, 1, 1])
    query = q_col.text_input("Suche (ISIN / Symbol / Name)", key="tr_universe_query")

    asset_counts = repo.count_by_asset_class()
    country_counts = repo.count_by_country()
    asset_options = ["Alle"] + sorted(asset_counts.keys())
    country_options = ["Alle"] + sorted(country_counts.keys())

    asset = ac_col.selectbox("Asset Class", asset_options, key="tr_universe_asset")
    country = co_col.selectbox("Land", country_options, key="tr_universe_country")
    limit = int(p_col.selectbox("Limit", [25, 50, 100, 200], index=1, key="tr_universe_limit"))

    asset_filter = None if asset == "Alle" else asset
    country_filter = None if country == "Alle" else country
    total_rows = repo.count(query=query or None, asset_class=asset_filter, country=country_filter)
    page_raw = st.number_input("Seite", min_value=1, value=1, key="tr_universe_page")
    page = int(page_raw or 1)
    offset = max(0, (page - 1) * limit)

    rows = repo.search(
        query=query or None,
        asset_class=asset_filter,
        country=country_filter,
        limit=limit,
        offset=offset,
    )
    st.caption(f"Treffer: {total_rows:,}")

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "isin": st.column_config.TextColumn("ISIN"),
                "symbol": st.column_config.TextColumn("Symbol"),
                "instrument_name": st.column_config.TextColumn("Name"),
                "country": st.column_config.TextColumn("Land"),
                "asset_class": st.column_config.TextColumn("Asset Class"),
                "source_url": st.column_config.TextColumn("Quelle"),
                "source_last_refreshed_at": st.column_config.TextColumn("Aktualisiert am"),
            },
        )
    else:
        st.info("Keine Einträge für die aktuellen Filter.")

    st.markdown("### Geladene Liste (ungefiltert)")
    snap_c1, snap_c2 = st.columns([1, 1])
    snapshot_limit = int(
        snap_c1.selectbox("Snapshot-Limit", [50, 100, 200, 500], index=1, key="tr_universe_snapshot_limit")
    )
    snapshot_page_raw = snap_c2.number_input(
        "Snapshot-Seite",
        min_value=1,
        value=1,
        key="tr_universe_snapshot_page",
    )
    snapshot_page = int(snapshot_page_raw or 1)
    snapshot_total = repo.count(query=None, asset_class=None, country=None)
    snapshot_offset = max(0, (snapshot_page - 1) * snapshot_limit)
    snapshot_rows = repo.search(
        query=None,
        asset_class=None,
        country=None,
        limit=snapshot_limit,
        offset=snapshot_offset,
    )
    st.caption(f"Snapshot gesamt: {snapshot_total:,}")
    if snapshot_rows:
        st.dataframe(
            pd.DataFrame(snapshot_rows),
            use_container_width=True,
            hide_index=True,
            column_config={
                "isin": st.column_config.TextColumn("ISIN"),
                "symbol": st.column_config.TextColumn("Symbol"),
                "instrument_name": st.column_config.TextColumn("Name"),
                "country": st.column_config.TextColumn("Land"),
                "asset_class": st.column_config.TextColumn("Asset Class"),
                "source_url": st.column_config.TextColumn("Quelle"),
                "source_last_refreshed_at": st.column_config.TextColumn("Aktualisiert am"),
            },
        )
    else:
        st.info("Noch kein Snapshot geladen.")

    with st.expander("Technische Details", expanded=False):
        st.code(
            "\n".join(
                [
                    f"source_url: {meta.get('source_url') or '-'}",
                    f"source_hash: {meta.get('source_hash') or '-'}",
                    f"valid_rows: {meta.get('valid_rows') or '-'}",
                    f"invalid_rows: {meta.get('invalid_rows') or '-'}",
                    f"last_error: {meta.get('last_error') or '-'}",
                ]
            ),
            language="text",
        )


