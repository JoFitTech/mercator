"""Repository-Schicht für lesenden und schreibenden Zugriff auf MySQL."""

from __future__ import annotations

import pandas as pd

from src.db.mysql_client import MySQLClient


class MySQLRepository:
    """Kapselt SQL-nahe Persistenzmethoden für bereinigte Daten."""

    def __init__(self, client: MySQLClient) -> None:
        self.client = client

    def save_clean_trades(self, trades_df: pd.DataFrame) -> int:
        """Speichert bereinigte Trades in MySQL.

        Returns:
            int: Anzahl verarbeiteter Zeilen (aktuell Platzhalter).
        """
        # TODO: INSERT/UPSERT-SQL finalisieren, sobald Zielschema fixiert ist.
        return len(trades_df.index)

    def fetch_trades(self, limit: int = 100) -> pd.DataFrame:
        """Lädt eine begrenzte Menge Trade-Datensätze aus MySQL."""
        # TODO: Reale SQL-Abfrage ergänzen.
        return pd.DataFrame()

    def fetch_trade_by_ticker(self, ticker: str) -> pd.DataFrame:
        """Lädt Trades für einen einzelnen Ticker."""
        # TODO: Reale SQL-Abfrage ergänzen.
        return pd.DataFrame()

    def fetch_dashboard_metrics(self) -> dict:
        """Liefert KPI-Rohwerte für das Dashboard."""
        # TODO: KPI-Aggregationen aus MySQL implementieren.
        return {}
