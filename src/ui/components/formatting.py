"""Zentrale UI-Formatierung fuer konsistente Anzeige in allen Seiten."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

EMPTY_VALUE = "—"



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

