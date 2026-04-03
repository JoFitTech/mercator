"""MySQL-Client für Verbindungsmanagement und Schema-Initialisierung."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import mysql.connector
from mysql.connector import Error, MySQLConnection

from src.config.settings import MySqlTargetSettings
from src.db.schema import MYSQL_SCHEMA_STATEMENTS


class MySqlClient:
    """Verantwortet Verbindungsaufbau, Verbindungsprüfung und Schema-Setup."""

    def __init__(self, settings: MySqlTargetSettings) -> None:
        self._settings = settings

    @property
    def target_name(self) -> str:
        """Liefert den Namen des konfigurierten MySQL-Ziels."""

        return self._settings.name

    @contextmanager
    def connection(self, include_database: bool = True) -> Iterator[MySQLConnection]:
        """Öffnet und schließt eine MySQL-Verbindung als Context Manager.

        Args:
            include_database: Steuert, ob direkt mit Zieldatenbank verbunden wird.

        Yields:
            Eine aktive MySQL-Verbindung.
        """

        conn = mysql.connector.connect(
            **self._settings.mysql_connection_kwargs(include_database=include_database)
        )
        try:
            yield conn
        finally:
            if conn.is_connected():
                conn.close()

    def test_connection(self) -> tuple[bool, str]:
        """Testet die MySQL-Erreichbarkeit mit kurzem Status-Text.

        Returns:
            Tupel mit Erfolgsflag und technischem Status-Text.
        """

        try:
            with self.connection(include_database=True):
                return True, f"Connection to target '{self._settings.name}' successful."
        except Error as exc:
            return False, f"Connection to target '{self._settings.name}' failed: {exc}"

    def initialize_schema(self) -> None:
        """Initialisiert die Tabellenstruktur anhand der DDL-Statements."""

        if self._settings.create_database:
            self._create_database_if_requested()

        with self.connection(include_database=True) as conn:
            with conn.cursor() as cursor:
                for statement in MYSQL_SCHEMA_STATEMENTS:
                    cursor.execute(statement)
            conn.commit()

    def _create_database_if_requested(self) -> None:
        """Legt die Datenbank optional an, falls explizit aktiviert."""

        with self.connection(include_database=False) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    (
                        "CREATE DATABASE IF NOT EXISTS "
                        f"`{self._settings.database}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                )
            conn.commit()
