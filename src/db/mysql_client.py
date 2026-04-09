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

    def initialize_schema(self) -> list[str]:
        """Initialisiert die Tabellenstruktur und führt Schema-Anpassungen durch.

        Returns:
            Liste der durchgeführten Aktionen (für Logging/Bericht).
        """

        actions: list[str] = []
        if self._settings.create_database:
            if self._create_database_if_requested():
                actions.append(f"Database `{self._settings.database}` created.")

        with self.connection(include_database=True) as conn:
            with conn.cursor() as cursor:
                # 1. Basis-Tabellen anlegen
                for statement in MYSQL_SCHEMA_STATEMENTS:
                    cursor.execute(statement)
                # (Hier verzichten wir auf explizites Logging pro CREATE TABLE IF NOT EXISTS)

                # 2. Spalten-Migrationen (idempotent)
                # --- companies ---
                if not self._column_exists(cursor, "companies", "company_key"):
                    cursor.execute("ALTER TABLE companies ADD COLUMN company_key VARCHAR(64) NULL FIRST")
                    actions.append("companies: Added `company_key`.")
                
                # Check for other missing columns in companies
                cols_to_check_companies = [
                    ("company_cik", "VARCHAR(32) NULL UNIQUE"),
                    ("current_symbol", "VARCHAR(20) NULL"),
                    ("profile_status", "VARCHAR(32) NOT NULL DEFAULT 'NOT_REQUESTED'"),
                    ("profile_reason", "VARCHAR(255) NULL"),
                    ("first_seen_at", "DATETIME NULL"),
                    ("last_seen_at", "DATETIME NULL"),
                    ("market_cap", "BIGINT NULL"),
                    ("price", "DECIMAL(18,4) NULL"),
                    ("currency", "VARCHAR(10) NULL"),
                    ("isin", "VARCHAR(32) NULL"),
                    ("cusip", "VARCHAR(32) NULL"),
                    ("exchange", "VARCHAR(64) NULL"),
                    ("exchange_full_name", "VARCHAR(128) NULL"),
                    ("industry", "VARCHAR(128) NULL"),
                    ("sector", "VARCHAR(128) NULL"),
                    ("country", "VARCHAR(64) NULL"),
                    ("website", "VARCHAR(255) NULL"),
                    ("description", "TEXT NULL"),
                    ("ceo", "VARCHAR(255) NULL"),
                    ("full_time_employees", "VARCHAR(32) NULL"),
                    ("ipo_date", "DATE NULL"),
                    ("is_etf", "BOOLEAN NULL"),
                    ("is_actively_trading", "BOOLEAN NULL"),
                    ("is_adr", "BOOLEAN NULL"),
                    ("is_fund", "BOOLEAN NULL"),
                    ("profile_updated_at", "DATETIME NULL"),
                ]
                for col_name, col_def in cols_to_check_companies:
                    if not self._column_exists(cursor, "companies", col_name):
                        cursor.execute(f"ALTER TABLE companies ADD COLUMN {col_name} {col_def}")
                        actions.append(f"companies: Added `{col_name}`.")

                # --- insider_trades ---
                cols_to_check_trades = [
                    ("company_key", "VARCHAR(64) NULL"),
                    ("symbol_at_trade", "VARCHAR(20) NULL"),
                    ("profile_status", "VARCHAR(32) NOT NULL DEFAULT 'NOT_REQUESTED'"),
                    ("profile_reason", "VARCHAR(255) NULL"),
                    ("filing_date", "DATE NULL"),
                    ("transaction_date", "DATE NULL"),
                    ("reporting_cik", "VARCHAR(32) NULL"),
                    ("company_cik", "VARCHAR(32) NULL"),
                    ("reporting_name", "VARCHAR(255) NULL"),
                    ("type_of_owner", "VARCHAR(255) NULL"),
                    ("transaction_type", "VARCHAR(64) NULL"),
                    ("acquisition_or_disposition", "CHAR(1) NULL"),
                    ("direct_or_indirect", "CHAR(1) NULL"),
                    ("form_type", "VARCHAR(16) NULL"),
                    ("security_name", "VARCHAR(255) NULL"),
                    ("qty", "BIGINT NULL"),
                    ("price", "DECIMAL(18,4) NULL"),
                    ("fetched_at", "DATETIME NOT NULL"),
                    ("gate_status", "VARCHAR(32) NOT NULL DEFAULT 'PENDING'"),
                    ("gate_reason", "VARCHAR(255) NULL"),
                    ("trade_value_estimated", "DECIMAL(20,4) NULL"),
                    ("source_url", "VARCHAR(512) NULL"),
                    ("dedupe_key", "CHAR(64) NOT NULL"),
                ]
                for col_name, col_def in cols_to_check_trades:
                    if not self._column_exists(cursor, "insider_trades", col_name):
                        cursor.execute(f"ALTER TABLE insider_trades ADD COLUMN {col_name} {col_def}")
                        actions.append(f"insider_trades: Added `{col_name}`.")

                # 3. Daten-Migration (Keys befüllen)
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

                # 4. PK-Migration für 'companies' abschließen
                cursor.execute("SHOW KEYS FROM companies WHERE Key_name = 'PRIMARY' AND Column_name = 'company_key'")
                if cursor.fetchone() is None:
                    if self._has_primary_key(cursor, "companies"):
                        cursor.execute("ALTER TABLE companies DROP PRIMARY KEY")
                        actions.append("companies: Dropped old Primary Key.")
                    
                    cursor.execute("UPDATE companies SET company_key = CONCAT('SYM:', COALESCE(current_symbol, 'UNKNOWN')) WHERE company_key IS NULL")
                    cursor.execute("ALTER TABLE companies MODIFY company_key VARCHAR(64) NOT NULL")
                    cursor.execute("ALTER TABLE companies ADD PRIMARY KEY (company_key)")
                    actions.append("companies: Set `company_key` as Primary Key.")

                # Nach PK-Wechsel Altfelder aufräumen
                if companies_has_legacy_symbol:
                    cursor.execute("ALTER TABLE companies MODIFY symbol VARCHAR(20) NULL")
                if trades_has_legacy_symbol:
                    cursor.execute("ALTER TABLE insider_trades MODIFY symbol VARCHAR(20) NULL")

                # 5. Constraints und Indizes
                if not self._constraint_exists(cursor, "insider_trades", "fk_insider_trades_company_key"):
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
                    actions.append("insider_trades: Added Foreign Key `fk_insider_trades_company_key`.")

                # Dedupe-Key Index
                cursor.execute("SHOW KEYS FROM insider_trades WHERE Key_name = 'uq_insider_trades_dedupe_key'")
                if cursor.fetchone() is None:
                    cursor.execute("ALTER TABLE insider_trades ADD UNIQUE INDEX uq_insider_trades_dedupe_key (dedupe_key)")
                    actions.append("insider_trades: Added Unique Index `uq_insider_trades_dedupe_key`.")

            conn.commit()
        return actions

    def _create_database_if_requested(self) -> bool:
        """Legt die Datenbank optional an, falls explizit aktiviert.

        Returns:
            bool: True, wenn die Datenbank neu angelegt wurde.
        """

        created = False
        with self.connection(include_database=False) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SHOW DATABASES LIKE '{self._settings.database}'")
                if not cursor.fetchone():
                    cursor.execute(
                        f"CREATE DATABASE `{self._settings.database}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                    created = True
            conn.commit()
        return created
