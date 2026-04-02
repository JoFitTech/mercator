"""Datenmodell für bereinigte Insider-Trades."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class InsiderTrade:
    """Transportobjekt für Insider-Trade-Daten zwischen Pipeline-Bausteinen."""

    symbol: str
    filing_date: datetime | None = None
    transaction_date: datetime | None = None
    reporting_cik: str | None = None
    company_cik: str | None = None
    transaction_type: str | None = None
    securities_owned: float | None = None
    reporting_name: str | None = None
    type_of_owner: str | None = None
    acquisition_or_disposition: str | None = None
    direct_or_indirect: str | None = None
    form_type: str | None = None
    qty: float | None = None
    price: float | None = None
    security_name: str | None = None
    source_url: str | None = None
    fetched_at: datetime | None = None
    first_seen_at: datetime | None = None
    gate_status: str = "PENDING"
    dedupe_key: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)
