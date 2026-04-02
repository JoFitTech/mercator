"""Datums-Helferfunktionen für Preprocessing und UI."""

from __future__ import annotations

from datetime import datetime


def parse_iso_date(value: str) -> datetime | None:
    """Parst ein ISO-Datum defensiv und liefert bei Fehler `None` zurück."""
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
