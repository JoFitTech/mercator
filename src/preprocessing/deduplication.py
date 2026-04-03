"""Funktionen zur technischen Deduplizierung von Datensätzen."""

from __future__ import annotations

import hashlib
from typing import Any


def build_dedupe_key(normalized_trade: dict[str, Any]) -> str:
    """Erzeugt technischen Schlüssel für Deduplizierung.

    Rückgabe:
        Stabiler SHA256-Hash über Kernattribute.
    """

    fingerprint = "|".join(
        [
            str(normalized_trade.get("symbol", "")),
            str(normalized_trade.get("filing_date", "")),
            str(normalized_trade.get("transaction_date", "")),
            str(normalized_trade.get("reporting_cik", "")),
            str(normalized_trade.get("company_cik", "")),
            str(normalized_trade.get("transaction_type", "")),
            str(normalized_trade.get("qty", "")),
            str(normalized_trade.get("price", "")),
        ]
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
