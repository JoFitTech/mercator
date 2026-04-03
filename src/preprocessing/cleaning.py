"""Orchestrierung der Bereinigung und Transformation von Rohdaten."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.preprocessing.deduplication import build_dedupe_key
from src.preprocessing.normalization import parse_datetime, parse_float


def normalize_insider_trade(raw_trade: dict[str, Any], fetched_at: datetime | None = None) -> dict[str, Any]:
    """Transformiert ein FMP-Rohobjekt in das Projektzielschema.

    Parameter:
        raw_trade: Unverändertes Objekt aus dem FMP-Feed.
        fetched_at: Optionaler Importzeitpunkt.

    Rückgabe:
        Normalisierter Datensatz inklusive `dedupe_key`.
    """

    now = fetched_at or datetime.now(timezone.utc)
    qty = parse_float(raw_trade.get("securitiesTransacted"), "securitiesTransacted")
    price = parse_float(raw_trade.get("price"), "price")
    
    # trade_value_estimated = qty * price
    trade_value_estimated = (qty * price) if qty is not None and price is not None else None
    
    # Fachliche Regel: Wenn Preis 0, ist der Schätzwert oft nicht sinnvoll berechenbar (Awards etc.)
    if trade_value_estimated == 0 and price == 0:
        trade_value_estimated = None

    normalized = {
        "symbol": str(raw_trade.get("symbol", "")).strip().upper() or None,
        "filing_date": parse_datetime(raw_trade.get("filingDate"), "filingDate"),
        "transaction_date": parse_datetime(raw_trade.get("transactionDate"), "transactionDate"),
        "reporting_cik": raw_trade.get("reportingCik"),
        "company_cik": raw_trade.get("companyCik"),
        "transaction_type": raw_trade.get("transactionType"),
        "securities_owned": parse_float(raw_trade.get("securitiesOwned"), "securitiesOwned"),
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
