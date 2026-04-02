"""Domänenmodell für Insider-Transaktionen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class InsiderTrade:
    """Repräsentiert einen bereinigten Insider-Trade-Datensatz.

    Das Modell dient primär der Lesbarkeit und als Übergabetyp zwischen
    Preprocessing, Services und Repositories.
    """

    ticker: str
    company_name: str
    trade_date: date
    insider_name: Optional[str] = None
    transaction_type: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    source_record_id: Optional[str] = None
