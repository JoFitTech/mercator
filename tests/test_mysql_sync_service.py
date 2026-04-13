"""Tests für den kontrollierten MySQL-Sync-Service ohne echte DB-Verbindung."""

from __future__ import annotations

from typing import Any

from src.services.mysql_sync_service import MySqlSyncService


class _SourceCompanyRepository:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def list_companies(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        return self._rows[offset : offset + limit]


class _TargetCompanyRepository:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def upsert_company(self, row: dict[str, Any]) -> None:
        self.rows.append(row)


class _SourceTradeRepository:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def list_latest_trades(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        return self._rows[offset : offset + limit]


class _TargetTradeRepository:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def upsert_trades(self, rows: list[dict[str, Any]]) -> int:
        self.rows.extend(rows)
        return len(rows)


class _DummyClient:
    def __init__(self, target_name: str) -> None:
        self.target_name = target_name


def test_sync_companies_skips_rows_without_symbol(monkeypatch) -> None:
    """Prüft, dass Company-Sync Einträge ohne company_key überspringt."""

    source_repo = _SourceCompanyRepository([
        {"company_key": "SYM:AAPL", "current_symbol": "AAPL", "company_name": "Apple"},
        {"current_symbol": "NOSYM", "company_name": "MissingKey"},
    ])
    target_repo = _TargetCompanyRepository()

    monkeypatch.setattr("src.services.mysql_sync_service.CompanyRepository", lambda client: source_repo if client.target_name == "local" else target_repo)

    service = MySqlSyncService(batch_size=1)
    result = service.sync_companies(_DummyClient("local"), _DummyClient("uni"))

    assert result.read_count == 2
    assert result.written_count == 1
    assert result.skipped_count == 1


def test_sync_trades_skips_rows_without_dedupe_key(monkeypatch) -> None:
    """Prüft, dass Trade-Sync Einträge ohne Dedupe-Key überspringt."""

    source_repo = _SourceTradeRepository([
        {"dedupe_key": "abc", "symbol": "AAPL"},
        {"dedupe_key": None, "symbol": "MSFT"},
    ])
    target_repo = _TargetTradeRepository()

    monkeypatch.setattr("src.services.mysql_sync_service.InsiderTradeRepository", lambda client: source_repo if client.target_name == "local" else target_repo)

    service = MySqlSyncService(batch_size=1)
    result = service.sync_insider_trades(_DummyClient("local"), _DummyClient("uni"))

    assert result.read_count == 2
    assert result.written_count == 1
    assert result.skipped_count == 1


def test_sync_all_reports_target_names(monkeypatch) -> None:
    """Prüft, dass die Gesamtzusammenfassung Quell- und Zielnamen ausweist."""

    source_company_repo = _SourceCompanyRepository([{"company_key": "SYM:AAPL", "current_symbol": "AAPL"}])
    target_company_repo = _TargetCompanyRepository()
    source_trade_repo = _SourceTradeRepository([{"dedupe_key": "abc", "symbol": "AAPL"}])
    target_trade_repo = _TargetTradeRepository()

    monkeypatch.setattr(
        "src.services.mysql_sync_service.CompanyRepository",
        lambda client: source_company_repo if client.target_name == "local" else target_company_repo,
    )
    monkeypatch.setattr(
        "src.services.mysql_sync_service.InsiderTradeRepository",
        lambda client: source_trade_repo if client.target_name == "local" else target_trade_repo,
    )

    service = MySqlSyncService(batch_size=100)
    summary = service.sync_all(_DummyClient("local"), _DummyClient("uni"))

    assert summary.source_target == "local"
    assert summary.target_target == "uni"
    assert summary.company_result.written_count == 1
    assert summary.insider_trade_result.written_count == 1


def test_determine_auto_direction_handles_string_timestamps(monkeypatch) -> None:
    """Prüft, dass String-Zeitstempel korrekt geparst und verglichen werden."""

    class _CompanyRepo:
        def __init__(self, client) -> None:
            self._client = client

        def get_max_updated_at(self):
            return "2026-04-13 10:00:00" if self._client.target_name == "local" else "2026-04-12 10:00:00"

    class _TradeRepo:
        def __init__(self, client) -> None:
            self._client = client

        def get_max_updated_at(self):
            return "2026-04-13 09:00:00" if self._client.target_name == "local" else "2026-04-12 11:00:00"

    monkeypatch.setattr("src.services.mysql_sync_service.CompanyRepository", _CompanyRepo)
    monkeypatch.setattr("src.services.mysql_sync_service.InsiderTradeRepository", _TradeRepo)

    service = MySqlSyncService()
    direction = service.determine_auto_direction(_DummyClient("local"), _DummyClient("uni"))

    assert direction == "local_to_uni"

