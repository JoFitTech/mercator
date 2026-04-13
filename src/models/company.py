"""Datenmodell für Unternehmensprofile aus dem FMP-Profile-Endpunkt."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Company:
    """Transportobjekt für ein bereinigtes Unternehmensprofil."""

    symbol: str
    company_name: str | None = None
    market_cap: float | None = None
    price: float | None = None
    currency: str | None = None
    cik: str | None = None
    isin: str | None = None
    cusip: str | None = None
    exchange: str | None = None
    exchange_full_name: str | None = None
    industry: str | None = None
    sector: str | None = None
    country: str | None = None
    website: str | None = None
    description: str | None = None
    ceo: str | None = None
    full_time_employees: str | None = None
    ipo_date: str | None = None
    is_etf: bool | None = None
    is_actively_trading: bool | None = None
    is_adr: bool | None = None
    is_fund: bool | None = None
    profile_updated_at: datetime | None = None
    source_system: str = "fmp"
    sync_version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    profile_payload: dict[str, Any] = field(default_factory=dict)
