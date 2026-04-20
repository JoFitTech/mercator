"""Orchestrierung der Bereinigung und Transformation von Rohdaten."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.preprocessing.deduplication import build_dedupe_key
from src.preprocessing.normalization import parse_datetime, parse_float
from src.services.buy_engine import normalize_security_type


def build_company_key(company_cik: Any, symbol: Any) -> str | None:
    """Erzeugt den kanonischen Company-Key."""
    cik = str(company_cik or "").strip()
    if cik:
        return f"CIK:{cik}"
    normalized_symbol = str(symbol or "").strip().upper()
    if normalized_symbol:
        return f"SYM:{normalized_symbol}"
    return None


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

    # Fachliche Entscheidung: Preise <= 0 gelten als explizit ungültig.
    # Solche Trades bleiben im Datensatz, werden aber weder sinnvoll bewertet
    # noch in das Pre-Gate übernommen.
    validation_status = "VALID"
    if price is not None and price <= 0:
        validation_status = "PRICE_INVALID"
        trade_value_estimated = None
    else:
        trade_value_estimated = (qty * price) if qty is not None and price is not None else None

    normalized_symbol = str(raw_trade.get("symbol", "")).strip().upper() or None
    company_cik = raw_trade.get("companyCik")
    filing_date = parse_datetime(raw_trade.get("filingDate"), "filingDate")
    filing_age_days = None
    if filing_date is not None:
        filing_age_days = max(0, (now.date() - filing_date.date()).days)

    normalized = {
        "symbol": normalized_symbol,
        "filing_date": filing_date,
        "transaction_date": parse_datetime(raw_trade.get("transactionDate"), "transactionDate"),
        "reporting_cik": raw_trade.get("reportingCik"),
        "company_cik": company_cik,
        "transaction_type": raw_trade.get("transactionType"),
        "securities_owned": parse_float(raw_trade.get("securitiesOwned"), "securitiesOwned"),
        "reporting_name": raw_trade.get("reportingName"),
        "type_of_owner": raw_trade.get("typeOfOwner"),
        "acquisition_or_disposition": str(raw_trade.get("acquisitionOrDisposition") or "")[:1].upper() or None,
        "direct_or_indirect": raw_trade.get("directOrIndirect"),
        "form_type": raw_trade.get("formType"),
        "qty": qty,
        "price": price,
        "trade_value_estimated": trade_value_estimated,
        "validation_status": validation_status,
        "security_name": raw_trade.get("securityName"),
        "normalized_instrument_type": normalize_security_type(raw_trade.get("securityName")),
        "filing_age_days": filing_age_days,
        "is_actively_trading": raw_trade.get("isActivelyTrading"),
        "source_url": raw_trade.get("url"),
        "fetched_at": now,
        "first_seen_at": now,
        "last_seen_at": now,
        "company_key": build_company_key(company_cik=company_cik, symbol=normalized_symbol),
        "symbol_at_trade": normalized_symbol,
        "gate_status": "PENDING",
        "gate_reason": None,
        "score_value": None,
        "score_class": None,
        "profile_status": "NOT_REQUESTED",
        "profile_reason": None,
        "tr_availability_state": "UNKNOWN",
        "tr_tradability_state": "UNKNOWN",
        "tr_match_confidence": "LOW",
        "raw_payload": raw_trade,
    }
    normalized["dedupe_key"] = build_dedupe_key(normalized)
    return normalized
