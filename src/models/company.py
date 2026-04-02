"""Domänenmodell für Unternehmensstammdaten."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Company:
    """Beschreibt ein Unternehmen, das in Trades oder Analysen vorkommt."""

    ticker: str
    name: str
    sector: Optional[str] = None
    country: Optional[str] = None
    isin: Optional[str] = None
