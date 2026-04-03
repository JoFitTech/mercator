"""Normalisierung und Typkonvertierung für FMP-Insider-Trade-Rohdaten."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

LOGGER = logging.getLogger(__name__)


def _parse_datetime(value: Any, field_name: str) -> datetime | None:
    """Parst Datumswerte robust in `datetime`-Objekte."""
    if value is None or value == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        LOGGER.warning("Datumsfeld konnte nicht geparst werden: %s=%s", field_name, value)
        return None
    return parsed.to_pydatetime()


def _parse_float(value: Any, field_name: str) -> float | None:
    """Konvertiert Werte defensiv in Float."""
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        LOGGER.warning("Zahlenfeld konnte nicht geparst werden: %s=%s", field_name, value)
        return None


def build_dedupe_key(normalized_trade: dict[str, Any]) -> str:
    """Erzeugt technischen Schlüssel für Deduplizierung.

    Parameter:
        normalized_trade: Normalisiertes Trade-Dict.

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


def normalize_insider_trade(raw_trade: dict[str, Any], fetched_at: datetime | None = None) -> dict[str, Any]:
    """Transformiert ein FMP-Rohobjekt in das Projektzielschema.

    Parameter:
        raw_trade: Unverändertes Objekt aus dem FMP-Feed.
        fetched_at: Optionaler Importzeitpunkt.

    Rückgabe:
        Normalisierter Datensatz inklusive `dedupe_key`.
    """

    now = fetched_at or datetime.now(timezone.utc)
    qty = _parse_float(raw_trade.get("securitiesTransacted"), "securitiesTransacted")
    price = _parse_float(raw_trade.get("price"), "price")
    
    trade_value_estimated = (qty * price) if qty is not None and price is not None else None
    if trade_value_estimated == 0 and price == 0:
        trade_value_estimated = None

    normalized = {
        "symbol": str(raw_trade.get("symbol", "")).strip().upper() or None,
        "filing_date": _parse_datetime(raw_trade.get("filingDate"), "filingDate"),
        "transaction_date": _parse_datetime(raw_trade.get("transactionDate"), "transactionDate"),
        "reporting_cik": raw_trade.get("reportingCik"),
        "company_cik": raw_trade.get("companyCik"),
        "transaction_type": raw_trade.get("transactionType"),
        "securities_owned": _parse_float(raw_trade.get("securitiesOwned"), "securitiesOwned"),
        "reporting_name": raw_trade.get("reportingName"),
        "type_of_owner": raw_trade.get("typeOfOwner"),
        "acquisition_or_disposition": raw_trade.get("acquistionOrDisposition"),
        "direct_or_indirect": raw_trade.get("directOrIndirect"),
        "form_type": raw_trade.get("formType"),
        "qty": qty,
        "price": price,
        "trade_value_estimated": trade_value_estimated,
        "security_name": raw_trade.get("securityName"),
        "source_url": raw_trade.get("url"),
        "fetched_at": now,
        "first_seen_at": now,
        "gate_status": "PENDING",
        "gate_reason": None,
        "raw_payload": raw_trade,
    }
    normalized["dedupe_key"] = build_dedupe_key(normalized)
    return normalized
