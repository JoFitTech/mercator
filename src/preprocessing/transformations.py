"""Transformationen für Datums- und Zahlenfelder."""

from __future__ import annotations

import pandas as pd


def parse_date_column(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Parst ein Datumsfeld robust mit `errors='coerce'`."""
    transformed = df.copy()
    if column_name in transformed.columns:
        transformed[column_name] = pd.to_datetime(transformed[column_name], errors="coerce")
    return transformed


def clean_numeric_column(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Konvertiert numerische Felder defensiv in Float-Werte."""
    transformed = df.copy()
    if column_name in transformed.columns:
        transformed[column_name] = pd.to_numeric(transformed[column_name], errors="coerce")
    return transformed
