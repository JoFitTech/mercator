from __future__ import annotations

from datetime import datetime, timezone

from src.models.watchlist import WatchlistItem
from src.services.stock_analysis_service import StockAnalysisService
from src.services.watchlist_service import WatchlistService


class _WatchlistRepoStub:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}
        self.deleted: list[str] = []

    def upsert_item(self, item: WatchlistItem) -> None:
        self.items[item.symbol] = {
            "symbol": item.symbol,
            "display_name": item.display_name,
            "notes": item.notes,
            "priority": item.priority,
            "active": item.active,
            "resolution_status": item.resolution_status,
        }

    def get_item(self, symbol: str) -> dict | None:
        return self.items.get(str(symbol).strip().upper())

    def list_items(self, active_only: bool = True) -> list[dict]:
        rows = list(self.items.values())
        if active_only:
            rows = [row for row in rows if bool(row.get("active", True))]
        return rows

    def list_unresolved_items(self, active_only: bool = True) -> list[dict]:
        rows = self.list_items(active_only=active_only)
        return [row for row in rows if str(row.get("resolution_status") or "").strip().upper() != "RESOLVED"]

    def delete_item(self, symbol: str) -> None:
        self.deleted.append(str(symbol).strip().upper())
        self.items.pop(str(symbol).strip().upper(), None)


class _DataQualityRepoStub:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {"AAPL": 2}

    def list_issues(self, symbol: str, unresolved_only: bool = True, limit: int = 1000) -> list[dict]:
        if symbol == "AAPL":
            return [{"issue_id": 1}, {"issue_id": 2}]
        return []


def test_watchlist_service_normalizes_symbol_and_delegates() -> None:
    repo = _WatchlistRepoStub()
    service = WatchlistService(repo)

    item = service.upsert_item(
        "aapl",
        display_name="Apple Inc.",
        notes="Core",
        priority="7",
        active=False,
        resolution_status="resolved",
    )

    assert item.symbol == "AAPL"
    assert item.priority == 7
    assert repo.get_item("AAPL")["resolution_status"] == "RESOLVED"


def test_watchlist_service_summary_counts_visible_states() -> None:
    repo = _WatchlistRepoStub()
    service = WatchlistService(repo)
    service.upsert_item("AAPL", display_name="Apple", active=True)
    service.upsert_item("MSFT", display_name="Microsoft", active=False, resolution_status="RESOLVED")

    summary = service.build_summary(active_only=False)

    assert summary["total_items"] == 2
    assert summary["active_items"] == 1
    assert summary["inactive_items"] == 1
    assert summary["unresolved_items"] == 1
    assert summary["resolved_items"] == 1


def test_stock_analysis_service_attaches_visible_status_text() -> None:
    watchlist_repo = _WatchlistRepoStub()
    watchlist_repo.upsert_item(
        WatchlistItem(
            symbol="AAPL",
            display_name="Apple Inc.",
            notes=None,
            priority=1,
            active=True,
            resolution_status="UNRESOLVED",
        )
    )
    analysis_service = StockAnalysisService(watchlist_repo, _DataQualityRepoStub())

    rows = analysis_service.list_watchlist_items_with_status(active_only=False)
    summary = analysis_service.build_watchlist_summary(active_only=False)

    assert rows[0]["profile_status_text"].startswith("Daten fuer Profil")
    assert rows[0]["price_status_text"].startswith("Daten fuer Kursdaten")
    assert rows[0]["data_quality_summary"] == "2 offene Datenqualitaetsprobleme."
    assert summary["total_items"] == 1
    assert "Watchlist" in summary["unresolved_text"]

