from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class TradeRepublicUniverseInstrument:
    isin: str
    symbol: str | None
    instrument_name: str | None
    country: str | None
    asset_class: str | None
    normalized_name: str | None = None


@dataclass(slots=True)
class TradeRepublicUniverseParseResult:
    instruments: list[TradeRepublicUniverseInstrument]
    total_rows: int
    valid_rows: int
    invalid_rows: int


@dataclass(slots=True)
class TradeRepublicUniverseImportSummary:
    status: str
    source_url: str
    source_type: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    inserted_rows: int
    source_hash: str
    refreshed_at: datetime | None
    error: str | None = None


@dataclass(slots=True)
class TradeRepublicUniverseSourcePayload:
    content: bytes
    content_type: str | None
    source_url: str
    source_type: str
    fetched_at: datetime
    source_hash: str

