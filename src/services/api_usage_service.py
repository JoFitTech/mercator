"""Service zur Verfolgung der API-Nutzung."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.db.repositories.api_usage_repository import ApiUsageRepository
from src.utils.logging_utils import get_logger


LOGGER = get_logger(__name__)


class ApiUsageService:
    """Verantwortet das Tracking und Abrufen von API-Nutzungsstatistiken."""

    def __init__(self, repository: ApiUsageRepository | None) -> None:
        self.repository = repository

    @staticmethod
    def _default_usage(provider: str, limit_count: int = 250) -> dict[str, Any]:
        today = date.today()
        return {
            "day_key": today,
            "provider": provider,
            "call_count": 0,
            "limit_count": limit_count,
            "remaining": limit_count,
            "last_request_at": None,
        }

    def track_call(self, provider: str = "fmp", limit: int = 250) -> None:
        """Registriert einen API-Aufruf."""
        if not self.repository:
            return
        
        today = date.today()
        try:
            self.repository.increment_usage(today, provider, limit)
        except Exception as exc:
            LOGGER.warning("API-Usage konnte nicht geschrieben werden (provider=%s): %s", provider, exc)

    def get_current_usage(self, provider: str = "fmp") -> dict[str, Any]:
        """Liefert die heutige Nutzung für einen Provider."""
        if not self.repository:
            return self._default_usage(provider)

        today = date.today()
        try:
            usage = self.repository.get_usage(today, provider)
        except Exception as exc:
            LOGGER.warning("API-Usage konnte nicht gelesen werden (provider=%s): %s", provider, exc)
            return self._default_usage(provider)

        if not usage:
            return self._default_usage(provider)

        usage["remaining"] = max(0, usage["limit_count"] - usage["call_count"])
        return usage
