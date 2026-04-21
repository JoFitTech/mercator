"""Service-Schicht für kontrollierte MySQL-Synchronisation zwischen zwei Zielen."""

from __future__ import annotations

import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any

from src.db.mysql_client import MySqlClient
from src.db.mysql_repository import (
    CompanyRepository,
    InsiderTradeRepository,
    AppFilterSettingsRepository,
    AppRuntimePreferencesRepository,
)


@dataclass(frozen=True)
class SyncResult:
    """Ergebnisstruktur für den Sync einer einzelnen Entität."""

    entity: str
    read_count: int
    written_count: int
    skipped_count: int
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SyncSummary:
    """Aggregiertes Ergebnis eines vollständigen MySQL-Sync-Laufs."""

    direction: str
    source_target: str
    target_target: str
    company_result: SyncResult
    insider_trade_result: SyncResult
    app_filter_settings_result: SyncResult | None = None
    app_runtime_preferences_result: SyncResult | None = None
    warnings: list[str] = field(default_factory=list)


class MySqlSyncService:
    """Koordiniert den Upsert-Sync zwischen zwei MySQL-Zielen mit last_write_wins-Semantik."""

    def __init__(self, batch_size: int = 500) -> None:
        self._batch_size = batch_size

    def _last_write_wins(self, src_row: dict[str, Any], tgt_row: dict[str, Any] | None) -> bool:
        """Bestimmt, ob die Quell-Zeile aktueller ist als das Ziel über updated_at."""
        if tgt_row is None:
            return True
        src_updated = src_row.get("updated_at")
        tgt_updated = tgt_row.get("updated_at")
        if src_updated is None or tgt_updated is None:
            return True
        # Quell-updated_at >= Ziel-updated_at bedeutet neuere/gleiche Version
        try:
            src_dt = pd.Timestamp(str(src_updated) if src_updated else datetime.min)  # type: ignore
            tgt_dt = pd.Timestamp(str(tgt_updated) if tgt_updated else datetime.min)  # type: ignore
            return src_dt >= tgt_dt
        except (TypeError, ValueError):
            return True

    def sync_companies(self, source_client: MySqlClient, target_client: MySqlClient) -> SyncResult:
        """Synchronisiert Unternehmen von Quelle zu Ziel per Upsert.

        Args:
            source_client: Quell-MySQL-Client.
            target_client: Ziel-MySQL-Client.

        Returns:
            SyncResult mit Lese-/Schreibstatistiken.
        """

        source_repo = CompanyRepository(source_client)
        target_repo = CompanyRepository(target_client)

        read_count = 0
        written_count = 0
        skipped_count = 0
        offset = 0

        while True:
            batch = source_repo.list_companies(limit=self._batch_size, offset=offset)
            if not batch:
                break

            for row in batch:
                read_count += 1
                company_key = str(row.get("company_key") or "").strip()
                if not company_key:
                    skipped_count += 1
                    continue

                target_repo.upsert_company(row)
                written_count += 1

            offset += len(batch)

        return SyncResult(
            entity="companies",
            read_count=read_count,
            written_count=written_count,
            skipped_count=skipped_count,
        )

    def sync_insider_trades(self, source_client: MySqlClient, target_client: MySqlClient) -> SyncResult:
        """Synchronisiert Insider-Trades von Quelle zu Ziel per Upsert.

        Args:
            source_client: Quell-MySQL-Client.
            target_client: Ziel-MySQL-Client.

        Returns:
            SyncResult mit Lese-/Schreibstatistiken.
        """

        source_repo = InsiderTradeRepository(source_client)
        target_repo = InsiderTradeRepository(target_client)

        read_count = 0
        written_count = 0
        skipped_count = 0
        offset = 0

        while True:
            batch = source_repo.list_latest_trades(limit=self._batch_size, offset=offset)
            if not batch:
                break

            filtered_batch: list[dict[str, Any]] = []
            for row in batch:
                read_count += 1
                dedupe_key = str(row.get("dedupe_key") or "").strip()
                if not dedupe_key:
                    skipped_count += 1
                    continue
                filtered_batch.append(row)

            written_count += target_repo.upsert_trades(filtered_batch)
            offset += len(batch)

        return SyncResult(
            entity="insider_trades",
            read_count=read_count,
            written_count=written_count,
            skipped_count=skipped_count,
        )

    def sync_app_filter_settings(self, source_client: MySqlClient, target_client: MySqlClient) -> SyncResult:
        """Synchronisiert App-Filtereinstellungen mit last_write_wins über (setting_scope, setting_key)."""

        source_repo = AppFilterSettingsRepository(source_client)
        target_repo = AppFilterSettingsRepository(target_client)

        read_count = 0
        written_count = 0
        skipped_count = 0
        offset = 0

        while True:
            batch = source_repo.list_all(limit=self._batch_size, offset=offset)
            if not batch:
                break

            for row in batch:
                read_count += 1
                scope = str(row.get("setting_scope") or "").strip()
                key = str(row.get("setting_key") or "").strip()
                if not scope or not key:
                    skipped_count += 1
                    continue

                target_row = target_repo.get_by_business_key(scope, key)
                if self._last_write_wins(row, target_row):
                    target_repo.upsert(row)
                    written_count += 1

            offset += len(batch)

        return SyncResult(
            entity="app_filter_settings",
            read_count=read_count,
            written_count=written_count,
            skipped_count=skipped_count,
        )

    def sync_app_runtime_preferences(self, source_client: MySqlClient, target_client: MySqlClient) -> SyncResult:
        """Synchronisiert App-Laufzeiteinstellungen mit last_write_wins über preference_key."""

        source_repo = AppRuntimePreferencesRepository(source_client)
        target_repo = AppRuntimePreferencesRepository(target_client)

        read_count = 0
        written_count = 0
        skipped_count = 0
        offset = 0

        while True:
            batch = source_repo.list_all(limit=self._batch_size, offset=offset)
            if not batch:
                break

            for row in batch:
                read_count += 1
                pref_key = str(row.get("preference_key") or "").strip()
                if not pref_key:
                    skipped_count += 1
                    continue

                target_row = target_repo.get_by_business_key(pref_key)
                if self._last_write_wins(row, target_row):
                    target_repo.upsert(row)
                    written_count += 1

            offset += len(batch)

        return SyncResult(
            entity="app_runtime_preferences",
            read_count=read_count,
            written_count=written_count,
            skipped_count=skipped_count,
        )

    def sync_all(
        self,
        local_client: MySqlClient,
        uni_client: MySqlClient,
        direction: str = "local_to_uni",
    ) -> SyncSummary:
        """Führt den kontrollierten Sync in die gewünschte Richtung aus.

        Args:
            local_client: Lokaler MySQL-Client.
            uni_client: Uni-MySQL-Client.
            direction: Sync-Richtung (local_to_uni, uni_to_local, auto).

        Returns:
            SyncSummary mit Details zum Lauf.
        """

        actual_source = local_client
        actual_target = uni_client
        effective_direction = direction

        if direction == "auto":
            effective_direction = self.determine_auto_direction(local_client, uni_client)

        if effective_direction == "uni_to_local":
            actual_source = uni_client
            actual_target = local_client

        company_result = self.sync_companies(actual_source, actual_target)
        insider_trade_result = self.sync_insider_trades(actual_source, actual_target)
        app_filter_settings_result = self.sync_app_filter_settings(actual_source, actual_target)
        app_runtime_preferences_result = self.sync_app_runtime_preferences(actual_source, actual_target)

        return SyncSummary(
            direction=effective_direction,
            source_target=actual_source.target_name,
            target_target=actual_target.target_name,
            company_result=company_result,
            insider_trade_result=insider_trade_result,
            app_filter_settings_result=app_filter_settings_result,
            app_runtime_preferences_result=app_runtime_preferences_result,
        )

    def sync_startup_reconnect(
        self,
        local_client: MySqlClient,
        uni_client: MySqlClient,
    ) -> SyncSummary:
        """Startup-Reconnect-Sync mit fester Richtung local -> uni."""

        return self.sync_all(
            local_client=local_client,
            uni_client=uni_client,
            direction="local_to_uni",
        )

    def determine_auto_direction(self, local_client: MySqlClient, uni_client: MySqlClient) -> str:
        """Bestimmt die Sync-Richtung basierend auf dem neuesten Zeitstempel beider DBs."""
        local_repo = CompanyRepository(local_client)
        uni_repo = CompanyRepository(uni_client)
        local_trades_repo = InsiderTradeRepository(local_client)
        uni_trades_repo = InsiderTradeRepository(uni_client)

        try:
            l_comp = local_repo.get_max_updated_at()
            u_comp = uni_repo.get_max_updated_at()
            l_trade = local_trades_repo.get_max_updated_at()
            u_trade = uni_trades_repo.get_max_updated_at()

            # Wir nehmen das Maximum aller Tabellen je Ziel
            def _to_dt(val: Any) -> datetime:
                if not val:
                    return datetime.min
                if isinstance(val, datetime):
                    return val
                try:
                    return pd.Timestamp(val).to_pydatetime()
                except Exception:
                    return datetime.min

            l_max = max(_to_dt(l_comp), _to_dt(l_trade))
            u_max = max(_to_dt(u_comp), _to_dt(u_trade))

            if l_max >= u_max:
                return "local_to_uni"
            return "uni_to_local"
        except Exception:
            return "local_to_uni"  # Fallback
