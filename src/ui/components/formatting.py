"""Zentrale UI-Formatierung für konsistente Anzeige in allen Seiten."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

EMPTY_VALUE = "—"


_MISSING_STATUS_VALUES = {
    "",
    "-",
    "—",
    "N/A",
    "NONE",
    "NULL",
    "NICHT VERFÜGBAR",
    "NICHT VERFUEGBAR",
}

_INCOMPLETE_PROFILE_STATUSES = {
    "",
    "FAILED",
    "NOT_REQUESTED",
    "NOT_FOUND",
    "UNRESOLVED",
    "-",
    "—",
    "NICHT VERFÜGBAR",
    "NICHT VERFUEGBAR",
}



def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    text = str(value).strip()
    return text == "" or text.lower() in {"none", "nan", "n/a", "null"}


def _is_missing_ui_value(value: Any) -> bool:
    return _is_empty(value)


def _ui_text(value: Any, fallback: str = EMPTY_VALUE) -> str:
    return fallback if _is_missing_ui_value(value) else str(value).strip()


def _normalize_profile_status(value: Any) -> str:
    if _is_missing_ui_value(value):
        return ""
    return str(value).strip().upper()


def _profile_status_label(value: Any) -> str:
    status = _normalize_profile_status(value)
    if status == "FETCHED":
        return "Profil geladen"
    if status == "FAILED":
        return "Profil fehlgeschlagen"
    if status == "NOT_REQUESTED":
        return "Noch nicht geladen"
    if status in _MISSING_STATUS_VALUES:
        return "Unvollständig"
    return status


def _missing_profile_fields(profile: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    normalized_status = _normalize_profile_status(profile.get("profile_status"))
    if normalized_status in _INCOMPLETE_PROFILE_STATUSES:
        missing.append("Profilstatus")
    if _is_missing_ui_value(profile.get("sector")):
        missing.append("Sektor")
    if _is_missing_ui_value(profile.get("industry")):
        missing.append("Industrie")
    if _is_missing_ui_value(profile.get("market_cap")):
        missing.append("Market Cap")
    if _is_missing_ui_value(profile.get("company_name")):
        missing.append("Unternehmensname")
    if "description" in profile and _is_missing_ui_value(profile.get("description")):
        missing.append("Beschreibung")
    return missing


def _is_incomplete_profile(profile: dict[str, Any]) -> bool:
    return bool(_missing_profile_fields(profile))


def _normalize_website_url(value: Any) -> str | None:
    if _is_missing_ui_value(value):
        return None
    url = str(value).strip()
    lower = url.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return url
    if "." not in url:
        return None
    return f"https://{url}"



def _to_decimal(value: Any) -> Decimal | None:
    if _is_empty(value):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None



def format_empty(value: Any) -> str:
    return EMPTY_VALUE if _is_empty(value) else str(value).strip()



def format_currency(value: Any, currency: str = "$") -> str:
    amount = _to_decimal(value)
    if amount is None:
        return EMPTY_VALUE
    return f"{currency}{amount:,.0f}"



def format_number(value: Any) -> str:
    number = _to_decimal(value)
    if number is None:
        return EMPTY_VALUE
    return f"{number:,.0f}"



def format_score(value: Any) -> str:
    number = _to_decimal(value)
    if number is None:
        return EMPTY_VALUE
    return f"{number:.1f}"



def format_percent(value: Any) -> str:
    number = _to_decimal(value)
    if number is None:
        return EMPTY_VALUE
    return f"{number:.1f}%"



def format_date(value: Any) -> str:
    if _is_empty(value):
        return EMPTY_VALUE
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return EMPTY_VALUE
    return parsed.strftime("%d.%m.%Y")

