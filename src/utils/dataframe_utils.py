"""Generische DataFrame-Hilfsfunktionen."""

from __future__ import annotations

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
