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

    def _column_exists(self, cursor, table: str, column: str) -> bool:
        """Prüft, ob eine Spalte in einer Tabelle existiert."""

        cursor.execute(f"SHOW COLUMNS FROM {table} LIKE %s", (column,))
        return cursor.fetchone() is not None

    def _has_primary_key(self, cursor, table: str) -> bool:
        """Prüft, ob eine Tabelle bereits einen Primärschlüssel hat."""

        cursor.execute(f"SHOW KEYS FROM {table} WHERE Key_name = 'PRIMARY'")
        return cursor.fetchone() is not None

    def _constraint_exists(self, cursor, table: str, constraint: str) -> bool:
        """Prüft, ob ein Constraint existiert."""

        cursor.execute(
            "SELECT 1 FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s AND CONSTRAINT_NAME = %s",
            (table, constraint)
        )
        return cursor.fetchone() is not None

    def initialize_schema(self) -> None:
        """Initialisiert die Tabellenstruktur und führt Schema-Anpassungen durch."""

        if self._settings.create_database:
            self._create_database_if_requested()

        with self.connection(include_database=True) as conn:
            with conn.cursor() as cursor:
                for statement in MYSQL_SCHEMA_STATEMENTS:
                    cursor.execute(statement)

                # Konservative Schema-Migrationen für ältere Installationen.
                # Wir prüfen explizit auf Spaltenexistenz, da 'ALTER TABLE ... ADD COLUMN IF NOT EXISTS'
                # nicht in allen MySQL-Versionen stabil unterstützt wird.
                if not self._column_exists(cursor, "companies", "company_key"):
                    # Wir legen die Spalte erst mal als NULL an, um Datenmigration zu ermöglichen,
                    # bevor wir sie zum Primary Key machen.
                    cursor.execute("ALTER TABLE companies ADD COLUMN company_key VARCHAR(64) NULL FIRST")
                
                if not self._column_exists(cursor, "companies", "company_cik"):
                    cursor.execute("ALTER TABLE companies ADD COLUMN company_cik VARCHAR(32) NULL UNIQUE")
                
                if not self._column_exists(cursor, "companies", "current_symbol"):
                    cursor.execute("ALTER TABLE companies ADD COLUMN current_symbol VARCHAR(20) NULL")
                
                if not self._column_exists(cursor, "companies", "profile_status"):
                    cursor.execute("ALTER TABLE companies ADD COLUMN profile_status VARCHAR(32) NOT NULL DEFAULT 'NOT_REQUESTED'")
                
                if not self._column_exists(cursor, "companies", "profile_reason"):
                    cursor.execute("ALTER TABLE companies ADD COLUMN profile_reason VARCHAR(255) NULL")
                
                if not self._column_exists(cursor, "companies", "first_seen_at"):
                    cursor.execute("ALTER TABLE companies ADD COLUMN first_seen_at DATETIME NULL")
                
                if not self._column_exists(cursor, "companies", "last_seen_at"):
                    cursor.execute("ALTER TABLE companies ADD COLUMN last_seen_at DATETIME NULL")

                if not self._column_exists(cursor, "insider_trades", "company_key"):
                    cursor.execute("ALTER TABLE insider_trades ADD COLUMN company_key VARCHAR(64) NULL")
                
                if not self._column_exists(cursor, "insider_trades", "symbol_at_trade"):
                    cursor.execute("ALTER TABLE insider_trades ADD COLUMN symbol_at_trade VARCHAR(20) NULL")
                
                if not self._column_exists(cursor, "insider_trades", "profile_status"):
                    cursor.execute("ALTER TABLE insider_trades ADD COLUMN profile_status VARCHAR(32) NOT NULL DEFAULT 'NOT_REQUESTED'")
                
                if not self._column_exists(cursor, "insider_trades", "profile_reason"):
                    cursor.execute("ALTER TABLE insider_trades ADD COLUMN profile_reason VARCHAR(255) NULL")

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

                if companies_has_legacy_symbol:
                    # Wir machen das alte Symbol-Feld NULLABLE, damit INSERTs ohne dieses Feld nicht crashen,
                    # falls es in der DB noch existiert (Altlast von vor der company_key Migration).
                    cursor.execute("ALTER TABLE companies MODIFY symbol VARCHAR(20) NULL")
                
                if trades_has_legacy_symbol:
                    cursor.execute("ALTER TABLE insider_trades MODIFY symbol VARCHAR(20) NULL")

                # PK-Migration für 'companies' abschließen.
                cursor.execute("SHOW KEYS FROM companies WHERE Key_name = 'PRIMARY' AND Column_name = 'company_key'")
                if cursor.fetchone() is None:
                    if self._has_primary_key(cursor, "companies"):
                        cursor.execute("ALTER TABLE companies DROP PRIMARY KEY")
                    
                    # Sicherstellen, dass keine NULL-Werte verbleiben (Fallback auf Symbol falls Migration lückenhaft)
                    # Wir nutzen 'current_symbol' oder das alte 'symbol' Feld als Fallback.
                    cursor.execute("UPDATE companies SET company_key = CONCAT('SYM:', COALESCE(current_symbol, 'UNKNOWN')) WHERE company_key IS NULL")

                    cursor.execute("ALTER TABLE companies MODIFY company_key VARCHAR(64) NOT NULL")
                    cursor.execute("ALTER TABLE companies ADD PRIMARY KEY (company_key)")

                # Foreign Key für 'insider_trades' sicherstellen.
                if not self._constraint_exists(cursor, "insider_trades", "fk_insider_trades_company_key"):
                    # DATENKONSISTENZ: Sicherstellen, dass für alle in insider_trades vorkommenden
                    # company_key's ein Eintrag in companies existiert (Ghost Companies).
                    # Sonst schlägt der FOREIGN KEY Constraint fehl (Error 1452).
                    cursor.execute(
                        "INSERT IGNORE INTO companies (company_key, current_symbol, profile_status, profile_reason) "
                        "SELECT DISTINCT it.company_key, it.symbol_at_trade, 'NOT_REQUESTED', 'GHOST_FROM_MIGRATION' "
                        "FROM insider_trades it "
                        "LEFT JOIN companies c ON it.company_key = c.company_key "
                        "WHERE c.company_key IS NULL"
                    )

                    cursor.execute(
                        "ALTER TABLE insider_trades ADD CONSTRAINT fk_insider_trades_company_key "
                        "FOREIGN KEY (company_key) REFERENCES companies(company_key)"
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
