"""Basisfunktionen zur Normalisierung von Datentypen."""

from __future__ import annotations

import logging
from datetime import datetime
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
