"""Basisfunktionen zur Normalisierung von Datentypen."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import pandas as pd

LOGGER = logging.getLogger(__name__)


def parse_datetime(value: Any, field_name: str) -> datetime | None:
    """Parst Datumswerte robust in `datetime`-Objekte."""
    if value is None or value == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        LOGGER.warning("Datumsfeld konnte nicht geparst werden: %s=%s", field_name, value)
        return None
    return parsed.to_pydatetime()


def parse_float(value: Any, field_name: str) -> float | None:
    """Konvertiert Werte defensiv in Float."""
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        LOGGER.warning("Zahlenfeld konnte nicht geparst werden: %s=%s", field_name, value)
        return None


def _normalize_symbol(symbol: Any) -> str:
    return str(symbol or "").strip().upper()


def _parse_date(value: Any, field_name: str) -> date | None:
    parsed = parse_datetime(value, field_name)
    return parsed.date() if parsed is not None else None


def _first_present(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_company_profile_payload(
    payload: dict[str, Any],
    *,
    symbol: str,
    provider: str = "FMP",
    fetched_at: datetime | None = None,
) -> dict[str, Any]:
    """Normalisiert ein Provider-Profil fuer die bestehende companies-Tabelle."""

    normalized_symbol = _normalize_symbol(payload.get("symbol") or symbol)
    if not normalized_symbol:
        raise ValueError("Company profile requires a symbol.")

    market_cap = parse_float(payload.get("marketCap"), "marketCap")
    price = parse_float(payload.get("price"), "price")
    employees = payload.get("fullTimeEmployees")
    return {
        "company_key": f"SYM:{normalized_symbol}",
        "current_symbol": normalized_symbol,
        "company_name": payload.get("companyName") or payload.get("company_name") or normalized_symbol,
        "profile_status": "FETCHED",
        "profile_reason": "stock_import",
        "market_cap": int(market_cap) if market_cap is not None else None,
        "price": price,
        "currency": payload.get("currency"),
        "isin": payload.get("isin"),
        "cusip": payload.get("cusip"),
        "exchange": payload.get("exchangeShortName") or payload.get("exchange"),
        "exchange_full_name": payload.get("exchange"),
        "industry": payload.get("industry"),
        "sector": payload.get("sector"),
        "sector_raw": payload.get("sector"),
        "sector_normalized": payload.get("sector"),
        "sector_source": provider,
        "sector_resolution_method": "provider_profile",
        "sector_resolution_status": "RESOLVED" if payload.get("sector") else "UNRESOLVED",
        "profile_enriched_at": fetched_at,
        "profile_provider": provider,
        "country": payload.get("country"),
        "website": payload.get("website"),
        "description": payload.get("description"),
        "ceo": payload.get("ceo"),
        "full_time_employees": str(employees) if employees not in (None, "") else None,
        "ipo_date": _parse_date(payload.get("ipoDate"), "ipoDate"),
        "is_etf": bool(payload.get("isEtf", False)),
        "is_actively_trading": bool(payload.get("isActivelyTrading", True)),
        "is_adr": bool(payload.get("isAdr", False)),
        "is_fund": bool(payload.get("isFund", False)),
        "profile_updated_at": fetched_at,
        "source_system": provider,
    }


def normalize_historical_price_payload(
    rows: list[dict[str, Any]],
    *,
    symbol: str,
    provider: str = "FMP",
    fetched_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """Normalisiert FMP Historical-EOD-Zeilen fuer stock_price_history."""

    normalized_symbol = _normalize_symbol(symbol)
    normalized: list[dict[str, Any]] = []
    for row in rows:
        price_date = _parse_date(row.get("date") or row.get("price_date"), "date")
        if not normalized_symbol or price_date is None:
            continue
        normalized.append(
            {
                "symbol": normalized_symbol,
                "price_date": price_date,
                "open_price": parse_float(_first_present(row, ("open", "open_price")), "open"),
                "high_price": parse_float(_first_present(row, ("high", "high_price")), "high"),
                "low_price": parse_float(_first_present(row, ("low", "low_price")), "low"),
                "close_price": parse_float(_first_present(row, ("close", "close_price")), "close"),
                "adjusted_close": parse_float(_first_present(row, ("adjClose", "adjusted_close")), "adjClose"),
                "volume": int(parse_float(row.get("volume"), "volume") or 0) if row.get("volume") not in (None, "") else None,
                "provider": provider,
                "source_refreshed_at": fetched_at,
                "quality_status": "READY",
            }
        )
    return normalized


def normalize_fundamental_metric_payload(
    rows: list[dict[str, Any]],
    *,
    symbol: str,
    metric_fields: dict[str, str],
    period_type: str = "annual",
    provider: str = "FMP",
    fetched_at: datetime | None = None,
    unit: str | None = None,
) -> list[dict[str, Any]]:
    """Extrahiert ausgewaehlte Finanz-/Bewertungsmetriken aus FMP-Zeilen."""

    normalized_symbol = _normalize_symbol(symbol)
    normalized: list[dict[str, Any]] = []
    for row in rows:
        period_end = _parse_date(row.get("date") or row.get("period_end"), "date")
        if not normalized_symbol or period_end is None:
            continue
        for source_field, metric_name in metric_fields.items():
            value = parse_float(row.get(source_field), source_field)
            if value is None:
                continue
            normalized.append(
                {
                    "symbol": normalized_symbol,
                    "metric_name": metric_name,
                    "period_type": period_type,
                    "period_end": period_end,
                    "value": value,
                    "unit": unit,
                    "provider": provider,
                    "source_refreshed_at": fetched_at,
                    "quality_status": "READY",
                }
            )
    return normalized
