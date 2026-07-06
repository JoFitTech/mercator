"""Transport models for raw stock provider data and import runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class RawProviderResponse:
    """Raw provider payload metadata before clean normalization."""

    provider: str
    category: str
    request_hash: str
    status: str
    fetched_at: datetime
    response_id: str | None = None
    symbol: str | None = None
    request_params: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    source_url: str | None = None


@dataclass(slots=True)
class ImportRunSummary:
    """Summary for a watchlist or symbol import run."""

    import_run_id: str
    provider: str
    import_type: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str = "PENDING"
    symbols_requested: int = 0
    symbols_succeeded: int = 0
    symbols_failed: int = 0
    raw_responses_written: int = 0
    clean_records_written: int = 0
    error_message: str | None = None
