"""Bereinigungsschritte für Rohdaten aus Finanzdatensätzen."""

from __future__ import annotations

import pandas as pd


def drop_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Entfernt vollständig leere Zeilen aus einem DataFrame."""
    if df.empty:
        return df.copy()
    return df.dropna(how="all").copy()


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Vereinheitlicht Spaltennamen auf `snake_case`-ähnliche Schreibweise.

    Hinweis:
        Diese Heuristik ist bewusst einfach gehalten, um keine fachlichen
        Annahmen über den finalen Datensatz vorwegzunehmen.
    """
    normalized = df.copy()
    normalized.columns = [
        c.strip().lower().replace(" ", "_").replace("-", "_") for c in normalized.columns
    ]
    return normalized
