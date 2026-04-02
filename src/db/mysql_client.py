"""MySQL-Client für relationale Zieldaten."""

from __future__ import annotations

import mysql.connector
from mysql.connector import MySQLConnection

from src.config.settings import MySqlConfig


class MySqlClient:
    """Stellt MySQL-Verbindungen für Repositories bereit."""

    def __init__(self, config: MySqlConfig) -> None:
        self.config = config

    def connect(self) -> MySQLConnection:
        """Öffnet eine neue Verbindung."""
        return mysql.connector.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.user,
            password=self.config.password,
        )
