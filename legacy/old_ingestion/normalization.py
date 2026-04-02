"""Normalisierung von Feldern für spätere Datenbankpersistenz."""

from __future__ import annotations

import pandas as pd


def normalize_ticker_series(series: pd.Series) -> pd.Series:
    """Normalisiert Ticker-Symbole (Großbuchstaben, Whitespace entfernt)."""
    return series.astype(str).str.strip().str.upper()


def normalize_transaction_type(series: pd.Series) -> pd.Series:
    """Standardisiert Kauf-/Verkaufscodes mit einer minimalen Mapping-Heuristik.

    TODO:
        Finales Mapping an konkrete Werte des gewählten Datensatzes anpassen.
    """
    mapping = {
        "buy": "BUY",
        "purchase": "BUY",
        "sell": "SELL",
        "sale": "SELL",
    }
    lowered = series.astype(str).str.strip().str.lower()
    return lowered.map(mapping).fillna(lowered.str.upper())


def normalize_empty_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Hilfsfunktion für Tests und defensive Pipeline-Logik."""
    return df.copy()
