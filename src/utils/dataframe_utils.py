"""Generische DataFrame-Hilfsfunktionen."""

from __future__ import annotations

import math
import pandas as pd


def ensure_columns(df: pd.DataFrame, required_columns: list[str]) -> pd.DataFrame:
    """Stellt sicher, dass alle Pflichtspalten vorhanden sind.

    Fehlende Spalten werden mit `pd.NA` angelegt, um Folgefehler in der
    Pipeline zu vermeiden.
    """
    out = df.copy()
    for column in required_columns:
        if column not in out.columns:
            out[column] = pd.NA
    return out


def format_mcap(value: float | int | None, currency: str = "USD") -> str:
    """Formatiert einen Market-Cap-Wert lesbar mit Währung.

    Gibt ``'- <currency>'`` zurück, wenn der Wert None oder NaN ist.
    """
    if value is None:
        return f"- {currency}"
    try:
        if math.isnan(float(value)):
            return f"- {currency}"
    except (TypeError, ValueError):
        return f"- {currency}"
    return f"{int(value):,} {currency}"

