"""Transport models for stock watchlists and data-quality issues."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class WatchlistItem:
    """Manual watchlist item that remains visible even if unresolved."""

    symbol: str
    id: int | None = None
    company_key: str | None = None
    display_name: str | None = None
    notes: str | None = None
    priority: int = 0
    active: bool = True
    resolution_status: str = "UNRESOLVED"
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class DataQualityIssue:
    """Visible data-quality issue for missing, stale, partial, or failed data."""

    symbol: str
    data_category: str
    severity: str
    status: str
    message: str
    detected_at: datetime
    issue_id: int | None = None
    source_refreshed_at: datetime | None = None
    resolved_at: datetime | None = None
