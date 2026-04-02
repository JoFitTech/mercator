"""Dateibasierter Datenimport für lokale Rohdatensätze."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class FileLoader:
    """Lädt CSV/Parquet-Dateien aus dem lokalen Datenordner.

    Die Klasse kapselt nur I/O. Fachliche Bereinigung erfolgt separat
    im Preprocessing-Bereich.
    """

    def load_csv(self, file_path: Path | str, **kwargs) -> pd.DataFrame:
        """Lädt eine CSV-Datei in ein DataFrame."""
        return pd.read_csv(file_path, **kwargs)

    def load_parquet(self, file_path: Path | str, **kwargs) -> pd.DataFrame:
        """Lädt eine Parquet-Datei in ein DataFrame."""
        return pd.read_parquet(file_path, **kwargs)
