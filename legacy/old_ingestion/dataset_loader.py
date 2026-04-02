"""Orchestrierung für den Import öffentlich verfügbarer Datensätze."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_sources.file_loader import FileLoader


class DatasetLoader:
    """Abstraktion für den initialen Datensatz-Import.

    TODO:
        Sobald der finale Uni-Datensatz feststeht, sollte hier eine klare
        Quelle (URL, API oder Dateiformat) verbindlich dokumentiert werden.
    """

    def __init__(self, file_loader: FileLoader | None = None) -> None:
        self.file_loader = file_loader or FileLoader()

    def load_from_path(self, dataset_path: Path | str) -> pd.DataFrame:
        """Lädt einen Datensatz anhand der Dateiendung.

        Args:
            dataset_path: Pfad auf CSV- oder Parquet-Datei.
        """
        path = Path(dataset_path)
        suffix = path.suffix.lower()

        if suffix == ".csv":
            return self.file_loader.load_csv(path)
        if suffix in {".parquet", ".pq"}:
            return self.file_loader.load_parquet(path)

        raise ValueError(f"Nicht unterstütztes Dateiformat: {suffix}")
