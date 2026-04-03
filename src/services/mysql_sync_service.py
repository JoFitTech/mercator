"""Service-Schicht für kontrollierte MySQL-Synchronisation zwischen zwei Zielen."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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

    def sync_all(self, source_client: MySqlClient, target_client: MySqlClient) -> SyncSummary:
        """Führt den vollständigen kontrollierten Sync für beide Tabellen aus.

        Args:
            source_client: Quell-MySQL-Client.
            target_client: Ziel-MySQL-Client.

        Returns:
            Zusammenfassung für Companies und Insider-Trades.
        """

        company_result = self.sync_companies(source_client, target_client)
        insider_trade_result = self.sync_insider_trades(source_client, target_client)

        return SyncSummary(
            source_target=source_client.target_name,
            target_target=target_client.target_name,
            company_result=company_result,
            insider_trade_result=insider_trade_result,
        )
