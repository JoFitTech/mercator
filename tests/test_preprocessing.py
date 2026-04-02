"""Basistests für Preprocessing-Module."""

import pandas as pd

from src.preprocessing.normalization import normalize_empty_dataframe


def test_normalize_empty_dataframe_returns_empty_copy() -> None:
    """Leerer Input soll ohne Fehler als leeres DataFrame zurückkommen."""
    df = pd.DataFrame()
    result = normalize_empty_dataframe(df)
    assert result.empty
    assert result is not df
