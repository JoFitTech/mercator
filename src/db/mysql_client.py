"""MySQL-Client für Mercator."""

from __future__ import annotations

import mysql.connector
from mysql.connector import MySQLConnection

from src.config.settings import AppSettings


class MySQLClient:
    """Verwaltet Verbindungsaufbau und Basiskonnektivität zu MySQL."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def connect(self) -> MySQLConnection:
        """Öffnet eine MySQL-Verbindung mit Parametern aus den Settings."""
        return mysql.connector.connect(
            host=self.settings.mysql_host,
            port=self.settings.mysql_port,
            database=self.settings.mysql_database,
            user=self.settings.mysql_user,
            password=self.settings.mysql_password,
        )
