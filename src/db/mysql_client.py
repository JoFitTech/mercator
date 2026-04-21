"""MySQL-Client für Verbindungsmanagement und Schema-Initialisierung."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import mysql.connector
from mysql.connector import Error, MySQLConnection
from mysql.connector import errorcode

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
            # is_connected() prueft intern auf unread results und kann selbst fehlschlagen.
            # Beim Cleanup schliessen wir die Verbindung daher direkt defensiv.
            try:
                conn.close()
            except Error:
                pass

    @contextmanager
    def get_connection(self) -> Iterator[MySQLConnection]:
        """Rueckwaertskompatibler Alias fuer bestehende Repository-Aufrufe."""

        with self.connection(include_database=True) as conn:
            yield conn

    def execute(self, sql: str, params: Any | None = None, *, commit: bool = True) -> int:
        """Fuehrt ein SQL-Statement aus und committed optional automatisch."""

        with self.connection(include_database=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params if params is not None else ())
                affected_rows = int(getattr(cursor, "rowcount", 0) or 0)
            if commit:
                conn.commit()
        return affected_rows

    def execute_many(self, sql: str, params_seq: list[dict[str, Any] | tuple[Any, ...]], *, commit: bool = True) -> int:
        """Fuehrt ein SQL-Statement als Batch (executemany) aus."""

        if not params_seq:
            return 0
        with self.connection(include_database=True) as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, params_seq)
                affected_rows = int(getattr(cursor, "rowcount", 0) or 0)
            if commit:
                conn.commit()
        return affected_rows

    @staticmethod
    def _query_has_row(cursor, query: str, params: tuple | None = None) -> bool:
        """Fuehrt eine Existenzabfrage aus und leert Restzeilen auf unbuffered Cursorn."""

        cursor.execute(query, params or ())
        row = cursor.fetchone()
        if getattr(cursor, "with_rows", False):
            cursor.fetchall()
        return row is not None

    def test_connection(self) -> tuple[bool, str]:
        """Testet die MySQL-Erreichbarkeit mit kurzem Status-Text.

        Returns:
            Tupel mit Erfolgsflag und technischem Status-Text.
        """

        try:
            with self.connection(include_database=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    _ = cursor.fetchone()
                    if getattr(cursor, "with_rows", False):
                        cursor.fetchall()
            return (
                True,
                f"MySQL target '{self._settings.name}' reachable "
                f"(host={self._settings.host}, port={self._settings.port}, "
                f"db={self._settings.database}, ssl={'off' if self._settings.ssl_disabled else 'on'}).",
            )
        except Error as exc:
            error_type, detail = self._classify_connection_error(exc)
            return (
                False,
                f"MySQL target '{self._settings.name}' connection failed [{error_type}] "
                f"(host={self._settings.host}, port={self._settings.port}, "
                f"db={self._settings.database}, ssl={'off' if self._settings.ssl_disabled else 'on'}): {detail}",
            )

    @staticmethod
    def _classify_connection_error(exc: Error) -> tuple[str, str]:
        """Klassifiziert haeufige MySQL-Verbindungsfehler fuer klare Diagnosen."""

        errno = getattr(exc, "errno", None)
        message = str(exc)

        if errno in {errorcode.ER_ACCESS_DENIED_ERROR, 1045}:
            return "auth_failed", "Authentication failed (user/password rejected)."
        if errno in {errorcode.ER_BAD_DB_ERROR, 1049}:
            return "database_missing", "Configured database does not exist."
        if errno in {2003, 2002}:
            return "network_unreachable", "Cannot reach MySQL host/port."
        if errno in {2005}:
            return "host_invalid", "MySQL hostname cannot be resolved."
        if errno in {2026}:
            return "ssl_error", "SSL/TLS handshake or certificate validation failed."
        if "timed out" in message.lower():
            return "timeout", "Connection attempt timed out."

        return "connection_error", message

    def _column_exists(self, cursor, table: str, column: str) -> bool:
        """Prüft, ob eine Spalte in einer Tabelle existiert."""

        return self._query_has_row(
            cursor,
            "SELECT 1 FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s "
            "LIMIT 1",
            (table, column),
        )

    def _has_primary_key(self, cursor, table: str) -> bool:
        """Prüft, ob eine Tabelle bereits einen Primärschlüssel hat."""

        return self._query_has_row(
            cursor,
            "SELECT 1 FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s "
            "AND CONSTRAINT_TYPE = 'PRIMARY KEY' LIMIT 1",
            (table,),
        )

    def _constraint_exists(self, cursor, table: str, constraint: str) -> bool:
        """Prüft, ob ein Constraint existiert."""

        return self._query_has_row(
            cursor,
            "SELECT 1 FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s AND CONSTRAINT_NAME = %s "
            "LIMIT 1",
            (table, constraint),
        )

    def _index_exists(self, cursor, table: str, index_name: str) -> bool:
        """Prueft, ob ein Indexname in einer Tabelle existiert."""

        return self._query_has_row(
            cursor,
            "SELECT 1 FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s "
            "LIMIT 1",
            (table, index_name),
        )

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
                    ("sector_raw", "VARCHAR(128) NULL"),
                    ("sector_normalized", "VARCHAR(128) NULL"),
                    ("sector_source", "VARCHAR(64) NULL"),
                    ("sector_resolution_method", "VARCHAR(64) NULL"),
                    ("sector_resolution_status", "VARCHAR(32) NOT NULL DEFAULT 'UNRESOLVED'"),
                    ("profile_enriched_at", "DATETIME NULL"),
                    ("profile_provider", "VARCHAR(64) NULL"),
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
                    ("source_system", "VARCHAR(32) NOT NULL DEFAULT 'fmp'"),
                    ("trade_republic_universe_status", "VARCHAR(32) NOT NULL DEFAULT 'UNKNOWN'"),
                    ("trade_republic_match_method", "VARCHAR(32) NOT NULL DEFAULT 'NONE'"),
                    ("trade_republic_match_confidence", "VARCHAR(16) NOT NULL DEFAULT 'LOW'"),
                    ("trade_republic_source_refreshed_at", "DATETIME NULL"),
                    ("trade_republic_reference_isin", "VARCHAR(32) NULL"),
                    ("trade_republic_reference_name", "VARCHAR(255) NULL"),
                    ("sync_version", "BIGINT NOT NULL DEFAULT 1"),
                    ("created_at", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
                    ("updated_at", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                ]
                for col_name, col_def in cols_to_check_companies:
                    if not self._column_exists(cursor, "companies", col_name):
                        cursor.execute(f"ALTER TABLE companies ADD COLUMN {col_name} {col_def}")
                        actions.append(f"companies: Added `{col_name}`.")

                if not self._index_exists(cursor, "companies", "uq_companies_current_symbol"):
                    cursor.execute("ALTER TABLE companies ADD UNIQUE INDEX uq_companies_current_symbol (current_symbol)")
                    actions.append("companies: Added Unique Index `uq_companies_current_symbol`.")

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
                    ("validation_status", "VARCHAR(32) NOT NULL DEFAULT 'VALID'"),
                    ("dashboard_valid", "BOOLEAN NOT NULL DEFAULT FALSE"),
                    ("score", "DECIMAL(6,2) NULL"),
                    ("score_class", "CHAR(1) NULL"),
                    ("source_url", "VARCHAR(512) NULL"),
                    ("trade_republic_universe_status", "VARCHAR(32) NOT NULL DEFAULT 'UNKNOWN'"),
                    ("trade_republic_match_method", "VARCHAR(32) NOT NULL DEFAULT 'NONE'"),
                    ("trade_republic_match_confidence", "VARCHAR(16) NOT NULL DEFAULT 'LOW'"),
                    ("trade_republic_source_refreshed_at", "DATETIME NULL"),
                    ("trade_republic_reference_isin", "VARCHAR(32) NULL"),
                    ("trade_republic_reference_name", "VARCHAR(255) NULL"),
                    ("dedupe_key", "CHAR(64) NOT NULL"),
                ]
                for col_name, col_def in cols_to_check_trades:
                    if not self._column_exists(cursor, "insider_trades", col_name):
                        cursor.execute(f"ALTER TABLE insider_trades ADD COLUMN {col_name} {col_def}")
                        actions.append(f"insider_trades: Added `{col_name}`.")

                # --- app_filter_settings ---
                filter_cols = [
                    ("setting_scope", "VARCHAR(64) NOT NULL"),
                    ("setting_key", "VARCHAR(128) NOT NULL"),
                    ("setting_value_json", "JSON NOT NULL"),
                    ("source_system", "VARCHAR(32) NOT NULL DEFAULT 'app'"),
                    ("sync_version", "BIGINT NOT NULL DEFAULT 1"),
                    ("created_at", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
                    ("updated_at", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                ]
                for col_name, col_def in filter_cols:
                    if not self._column_exists(cursor, "app_filter_settings", col_name):
                        cursor.execute(f"ALTER TABLE app_filter_settings ADD COLUMN {col_name} {col_def}")
                        actions.append(f"app_filter_settings: Added `{col_name}`.")
                if not self._index_exists(cursor, "app_filter_settings", "uq_app_filter_settings_scope_key"):
                    cursor.execute(
                        "ALTER TABLE app_filter_settings ADD UNIQUE INDEX uq_app_filter_settings_scope_key (setting_scope, setting_key)"
                    )
                    actions.append("app_filter_settings: Added Unique Index `uq_app_filter_settings_scope_key`.")

                # --- app_runtime_preferences ---
                preference_cols = [
                    ("preference_key", "VARCHAR(128) NOT NULL"),
                    ("preference_value_json", "JSON NOT NULL"),
                    ("source_system", "VARCHAR(32) NOT NULL DEFAULT 'app'"),
                    ("sync_version", "BIGINT NOT NULL DEFAULT 1"),
                    ("created_at", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
                    ("updated_at", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                ]
                for col_name, col_def in preference_cols:
                    if not self._column_exists(cursor, "app_runtime_preferences", col_name):
                        cursor.execute(f"ALTER TABLE app_runtime_preferences ADD COLUMN {col_name} {col_def}")
                        actions.append(f"app_runtime_preferences: Added `{col_name}`.")
                if not self._index_exists(cursor, "app_runtime_preferences", "uq_app_runtime_preferences_key"):
                    cursor.execute(
                        "ALTER TABLE app_runtime_preferences ADD UNIQUE INDEX uq_app_runtime_preferences_key (preference_key)"
                    )
                    actions.append("app_runtime_preferences: Added Unique Index `uq_app_runtime_preferences_key`.")

                # 3. Daten-Migration (Keys befüllen)
                companies_has_legacy_symbol = self._column_exists(cursor, "companies", "symbol")
                trades_has_legacy_symbol = self._column_exists(cursor, "insider_trades", "symbol")

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
                if not self._query_has_row(
                    cursor,
                    "SELECT 1 FROM information_schema.KEY_COLUMN_USAGE "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                    "AND CONSTRAINT_NAME = 'PRIMARY' AND COLUMN_NAME = %s LIMIT 1",
                    ("companies", "company_key"),
                ):
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
                if not self._index_exists(cursor, "insider_trades", "uq_insider_trades_dedupe_key"):
                    cursor.execute("ALTER TABLE insider_trades ADD UNIQUE INDEX uq_insider_trades_dedupe_key (dedupe_key)")
                    actions.append("insider_trades: Added Unique Index `uq_insider_trades_dedupe_key`.")

                # Querypfad-Indizes (idempotent) für echte UI- und Dashboard-Zugriffe.
                # Diese werden bewusst im Schema-Setup gehalten, damit Deployments ohne manuelle Migrationsschritte stabil bleiben.
                trade_indexes = [
                    ("idx_trades_transaction_filing", "transaction_date, filing_date"),
                    ("idx_trades_symbol_transaction", "symbol_at_trade, transaction_date"),
                    ("idx_trades_company_transaction", "company_key, transaction_date"),
                    ("idx_trades_gate_validation_transaction", "gate_status, validation_status, transaction_date"),
                    ("idx_trades_score", "score"),
                    ("idx_trades_tr_universe_status", "trade_republic_universe_status"),
                ]
                for index_name, index_cols in trade_indexes:
                    if not self._index_exists(cursor, "insider_trades", index_name):
                        cursor.execute(
                            f"ALTER TABLE insider_trades ADD INDEX {index_name} ({index_cols})"
                        )
                        actions.append(f"insider_trades: Added Index `{index_name}`.")

                if not self._index_exists(cursor, "companies", "idx_companies_active_symbol"):
                    cursor.execute(
                        "ALTER TABLE companies ADD INDEX idx_companies_active_symbol (is_actively_trading, current_symbol)"
                    )
                    actions.append("companies: Added Index `idx_companies_active_symbol`.")

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
                if not self._query_has_row(
                    cursor,
                    "SELECT 1 FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s LIMIT 1",
                    (self._settings.database,),
                ):
                    cursor.execute(
                        f"CREATE DATABASE `{self._settings.database}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                    created = True
            conn.commit()
        return created
