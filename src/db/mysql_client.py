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
        """Initialisiert die Tabellenstruktur und führt Schema-Anpassungen durch."""

        if self._settings.create_database:
            self._create_database_if_requested()

        with self.connection(include_database=True) as conn:
            with conn.cursor() as cursor:
                for statement in MYSQL_SCHEMA_STATEMENTS:
                    cursor.execute(statement)

                # Konservative Schema-Migrationen für ältere Installationen.
                cursor.execute(
                    "ALTER TABLE companies "
                    "ADD COLUMN IF NOT EXISTS company_key VARCHAR(64) NULL PRIMARY KEY"
                )
                cursor.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS company_cik VARCHAR(32) NULL UNIQUE")
                cursor.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS current_symbol VARCHAR(20) NULL")
                cursor.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS profile_status VARCHAR(32) NOT NULL DEFAULT 'NOT_REQUESTED'")
                cursor.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS profile_reason VARCHAR(255) NULL")
                cursor.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS first_seen_at DATETIME NULL")
                cursor.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS last_seen_at DATETIME NULL")

                cursor.execute("ALTER TABLE insider_trades ADD COLUMN IF NOT EXISTS company_key VARCHAR(64) NULL")
                cursor.execute("ALTER TABLE insider_trades ADD COLUMN IF NOT EXISTS symbol_at_trade VARCHAR(20) NULL")
                cursor.execute("ALTER TABLE insider_trades ADD COLUMN IF NOT EXISTS profile_status VARCHAR(32) NOT NULL DEFAULT 'NOT_REQUESTED'")
                cursor.execute("ALTER TABLE insider_trades ADD COLUMN IF NOT EXISTS profile_reason VARCHAR(255) NULL")

                cursor.execute("SHOW COLUMNS FROM companies LIKE 'symbol'")
                companies_has_legacy_symbol = cursor.fetchone() is not None
                cursor.execute("SHOW COLUMNS FROM insider_trades LIKE 'symbol'")
                trades_has_legacy_symbol = cursor.fetchone() is not None

                company_symbol_expr = "COALESCE(current_symbol, symbol, '')" if companies_has_legacy_symbol else "COALESCE(current_symbol, '')"
                cursor.execute(
                    "UPDATE companies SET company_key = "
                    "CASE WHEN COALESCE(company_cik,'') <> '' THEN CONCAT('CIK:', company_cik) "
                    f"ELSE CONCAT('SYM:', UPPER({company_symbol_expr})) END "
                    "WHERE company_key IS NULL OR company_key = ''"
                )
                if trades_has_legacy_symbol:
                    cursor.execute(
                        "UPDATE insider_trades SET symbol_at_trade = COALESCE(symbol_at_trade, symbol) "
                        "WHERE symbol_at_trade IS NULL"
                    )
                cursor.execute(
                    "UPDATE insider_trades SET company_key = "
                    "CASE WHEN COALESCE(company_cik,'') <> '' THEN CONCAT('CIK:', company_cik) "
                    f"ELSE CONCAT('SYM:', UPPER(COALESCE(symbol_at_trade{', symbol' if trades_has_legacy_symbol else ''}, ''))) END "
                    "WHERE company_key IS NULL OR company_key = ''"
                )
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
