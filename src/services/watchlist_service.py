"""Service fuer die manuelle Watchlist."""

from __future__ import annotations

from typing import Any

from src.db.repositories.watchlist_repository import WatchlistRepository
from src.models.watchlist import WatchlistItem


class WatchlistService:
    """Fasst Watchlist-CRUD und Normalisierung zusammen."""

    def __init__(self, repository: WatchlistRepository | None) -> None:
        self.repository = repository

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        return str(symbol or "").strip().upper()

    def get_item(self, symbol: str) -> dict[str, Any] | None:
        if self.repository is None:
            return None
        return self.repository.get_item(symbol)

    def list_items(self, active_only: bool = True) -> list[dict[str, Any]]:
        if self.repository is None:
            return []
        return self.repository.list_items(active_only=active_only)

    def list_unresolved_items(self, active_only: bool = True) -> list[dict[str, Any]]:
        if self.repository is None:
            return []
        if hasattr(self.repository, "list_unresolved_items"):
            return self.repository.list_unresolved_items(active_only=active_only)
        return [
            row
            for row in self.repository.list_items(active_only=active_only)
            if str(row.get("resolution_status") or "").strip().upper() != "RESOLVED"
        ]

    def upsert_item(
        self,
        symbol: str,
        *,
        company_key: str | None = None,
        display_name: str | None = None,
        notes: str | None = None,
        priority: int = 0,
        active: bool = True,
        resolution_status: str = "UNRESOLVED",
    ) -> WatchlistItem:
        if self.repository is None:
            raise RuntimeError("Watchlist repository is not available.")

        item = WatchlistItem(
            symbol=self._normalize_symbol(symbol),
            company_key=str(company_key).strip() if company_key else None,
            display_name=str(display_name).strip() if display_name else None,
            notes=str(notes).strip() if notes else None,
            priority=int(priority),
            active=bool(active),
            resolution_status=str(resolution_status or "UNRESOLVED").strip().upper() or "UNRESOLVED",
        )
        self.repository.upsert_item(item)
        return item

    def delete_item(self, symbol: str) -> None:
        if self.repository is None:
            raise RuntimeError("Watchlist repository is not available.")
        self.repository.delete_item(symbol)

    def build_summary(self, active_only: bool = False) -> dict[str, Any]:
        items = self.list_items(active_only=active_only)
        active_count = sum(1 for item in items if bool(item.get("active", True)))
        unresolved_count = sum(
            1 for item in items if str(item.get("resolution_status") or "").strip().upper() != "RESOLVED"
        )
        resolved_count = max(0, len(items) - unresolved_count)
        return {
            "total_items": len(items),
            "active_items": active_count,
            "inactive_items": len(items) - active_count,
            "unresolved_items": unresolved_count,
            "resolved_items": resolved_count,
        }
