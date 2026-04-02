"""Service für End-to-End-Datenimport in beide Datenbanken."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.data_sources.dataset_loader import DatasetLoader
from src.db.mongo_repository import MongoRepository
from src.db.mysql_repository import MySQLRepository
from src.preprocessing.cleaning import drop_empty_rows, standardize_column_names


@dataclass
class ImportSummary:
    """Gibt ein kompaktes Ergebnis des Importprozesses zurück."""

    raw_rows: int
    clean_rows: int
    mongo_written: int
    mysql_written: int


class ImportService:
    """Orchestriert Rohdatenimport, Bereinigung und Persistenz."""

    def __init__(
        self,
        dataset_loader: DatasetLoader,
        mongo_repository: MongoRepository,
        mysql_repository: MySQLRepository,
    ) -> None:
        self.dataset_loader = dataset_loader
        self.mongo_repository = mongo_repository
        self.mysql_repository = mysql_repository

    def import_from_path(self, dataset_path: str) -> ImportSummary:
        """Führt einen einfachen Importlauf für einen Dateipfad aus."""
        raw_df = self.dataset_loader.load_from_path(dataset_path)
        clean_df = standardize_column_names(drop_empty_rows(raw_df))

        mongo_written = self.mongo_repository.save_raw_trades(raw_df)
        mysql_written = self.mysql_repository.save_clean_trades(clean_df)

        return ImportSummary(
            raw_rows=len(raw_df.index),
            clean_rows=len(clean_df.index),
            mongo_written=mongo_written,
            mysql_written=mysql_written,
        )

    def import_dataframe(self, dataframe: pd.DataFrame) -> ImportSummary:
        """Alternative Importschnittstelle für bereits geladene DataFrames."""
        clean_df = standardize_column_names(drop_empty_rows(dataframe))
        return ImportSummary(
            raw_rows=len(dataframe.index),
            clean_rows=len(clean_df.index),
            mongo_written=self.mongo_repository.save_raw_trades(dataframe),
            mysql_written=self.mysql_repository.save_clean_trades(clean_df),
        )
