"""Service zur Verfolgung der API-Nutzung."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from src.db.mysql_repository import ApiUsageRepository


class ApiUsageService:
    """Verantwortet das Tracking und Abrufen von API-Nutzungsstatistiken."""

    def __init__(self, repository: ApiUsageRepository | None) -> None:
        self.repository = repository

    def track_call(self, provider: str = "fmp", limit: int = 250) -> None:
        """Registriert einen API-Aufruf."""
        if not self.repository:
            return
        
        today = date.today()
        self.repository.increment_usage(today, provider, limit)

    def get_current_usage(self, provider: str = "fmp") -> dict[str, Any]:
        """Liefert die heutige Nutzung für einen Provider."""
        if not self.repository:
            return {
                "day_key": date.today(),
                "provider": provider,
                "call_count": 0,
                "limit_count": 250,
                "remaining": 250,
                "last_request_at": None
            }
        
        today = date.today()
        usage = self.repository.get_usage(today, provider)
        
        if not usage:
            return {
                "day_key": today,
                "provider": provider,
                "call_count": 0,
                "limit_count": 250,
                "remaining": 250,
                "last_request_at": None
            }
        
        usage["remaining"] = max(0, usage["limit_count"] - usage["call_count"])
        return usage
