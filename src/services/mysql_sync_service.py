"""Service-Schicht für kontrollierte MySQL-Synchronisation zwischen zwei Zielen."""

from __future__ import annotations
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Literal

from src.db.mysql_client import MySqlClient
from src.db.mysql_repository import CompanyRepository, InsiderTradeRepository


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


class MySqlSyncService:
    """Koordiniert den expliziten Upsert-Sync zwischen zwei MySQL-Zielen."""

    def __init__(self, batch_size: int = 500) -> None:
        self._batch_size = batch_size

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
                symbol = str(row.get("symbol") or "").strip()
                if not symbol:
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

    def sync_all(
        self,
        local_client: MySqlClient,
        uni_client: MySqlClient,
        direction: Literal["local_to_uni", "uni_to_local", "auto"] = "local_to_uni",
    ) -> SyncSummary:
        """Führt den kontrollierten Sync in die gewünschte Richtung aus.

        Args:
            local_client: Lokaler MySQL-Client.
            uni_client: Uni-MySQL-Client.
            direction: Sync-Richtung oder 'auto' für Heuristik.

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

        return SyncSummary(
            direction=effective_direction,
            source_target=actual_source.target_name,
            target_target=actual_target.target_name,
            company_result=company_result,
            insider_trade_result=insider_trade_result,
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
                if not val: return datetime.min
                if isinstance(val, datetime): return val
                return datetime.min

            l_max = max(_to_dt(l_comp), _to_dt(l_trade))
            u_max = max(_to_dt(u_comp), _to_dt(u_trade))

            if l_max >= u_max:
                return "local_to_uni"
            return "uni_to_local"
        except Exception:
            return "local_to_uni"  # Fallback
