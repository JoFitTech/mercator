"""MySQL-Repositories für bereinigte Trades und Unternehmensprofile."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.db.mysql_client import MySqlClient


class InsiderTradeMySqlRepository:
    """Persistiert bereinigte Insider-Trades in der Tabelle `insider_trades`."""

    def __init__(self, client: MySqlClient) -> None:
        self.client = client
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Legt die Zieltabelle bei Bedarf an."""
        ddl = """
        CREATE TABLE IF NOT EXISTS insider_trades (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(16),
            filing_date DATETIME NULL,
            transaction_date DATETIME NULL,
            reporting_cik VARCHAR(64) NULL,
            company_cik VARCHAR(64) NULL,
            reporting_name VARCHAR(255) NULL,
            type_of_owner VARCHAR(128) NULL,
            transaction_type VARCHAR(64) NULL,
            acquisition_or_disposition VARCHAR(16) NULL,
            direct_or_indirect VARCHAR(16) NULL,
            form_type VARCHAR(32) NULL,
            security_name VARCHAR(255) NULL,
            qty DOUBLE NULL,
            price DOUBLE NULL,
            trade_value_estimated DOUBLE NULL,
            gate_status VARCHAR(32) NULL,
            source_url TEXT NULL,
            dedupe_key VARCHAR(64) NOT NULL,
            fetched_at DATETIME NULL,
            first_seen_at DATETIME NULL,
            UNIQUE KEY uk_dedupe_key (dedupe_key)
        )
        """
        with self.client.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()

    def upsert_trades(self, trades: list[dict[str, Any]]) -> int:
        """Schreibt bereinigte Trades als Upsert."""
        if not trades:
            return 0
        sql = """
        INSERT INTO insider_trades (
            symbol, filing_date, transaction_date, reporting_cik, company_cik,
            reporting_name, type_of_owner, transaction_type, acquisition_or_disposition,
            direct_or_indirect, form_type, security_name, qty, price,
            trade_value_estimated, gate_status, source_url, dedupe_key, fetched_at, first_seen_at
        ) VALUES (
            %(symbol)s, %(filing_date)s, %(transaction_date)s, %(reporting_cik)s, %(company_cik)s,
            %(reporting_name)s, %(type_of_owner)s, %(transaction_type)s, %(acquisition_or_disposition)s,
            %(direct_or_indirect)s, %(form_type)s, %(security_name)s, %(qty)s, %(price)s,
            %(trade_value_estimated)s, %(gate_status)s, %(source_url)s, %(dedupe_key)s, %(fetched_at)s, %(first_seen_at)s
        )
        ON DUPLICATE KEY UPDATE
            gate_status=VALUES(gate_status),
            fetched_at=VALUES(fetched_at),
            price=VALUES(price),
            qty=VALUES(qty),
            trade_value_estimated=VALUES(trade_value_estimated)
        """
        with self.client.connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, trades)
            conn.commit()
        return len(trades)

    def fetch_trades(self, filters: dict[str, Any] | None = None, limit: int = 500) -> pd.DataFrame:
        """Liest Trades für Explorer, Dashboard und Details."""
        filters = filters or {}
        clauses: list[str] = []
        params: dict[str, Any] = {"limit": limit}
        mapping = {
            "symbol": "t.symbol",
            "transaction_type": "t.transaction_type",
            "gate_status": "t.gate_status",
            "sector": "c.sector",
            "country": "c.country",
        }
        for field, sql_field in mapping.items():
            if filters.get(field):
                clauses.append(f"{sql_field} = %({field})s")
                params[field] = filters[field]

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
            SELECT t.*, c.company_name, c.sector, c.country
            FROM insider_trades t
            LEFT JOIN companies c ON c.symbol = t.symbol
            {where_sql}
            ORDER BY t.filing_date DESC
            LIMIT %(limit)s
        """
        with self.client.connect() as conn:
            return pd.read_sql(query, conn, params=params)

    def count_all(self) -> int:
        """Liefert Gesamtzahl bereinigter Datensätze."""
        with self.client.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM insider_trades")
                return int(cur.fetchone()[0])


class CompanyMySqlRepository:
    """Persistiert bereinigte Unternehmensprofile in `companies`."""

    def __init__(self, client: MySqlClient) -> None:
        self.client = client
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Legt die Company-Tabelle an."""
        ddl = """
        CREATE TABLE IF NOT EXISTS companies (
            symbol VARCHAR(16) PRIMARY KEY,
            company_name VARCHAR(255) NULL,
            market_cap DOUBLE NULL,
            price DOUBLE NULL,
            currency VARCHAR(16) NULL,
            cik VARCHAR(64) NULL,
            isin VARCHAR(64) NULL,
            cusip VARCHAR(64) NULL,
            exchange VARCHAR(64) NULL,
            exchange_full_name VARCHAR(128) NULL,
            industry VARCHAR(128) NULL,
            sector VARCHAR(128) NULL,
            country VARCHAR(64) NULL,
            website TEXT NULL,
            description TEXT NULL,
            ceo VARCHAR(128) NULL,
            full_time_employees VARCHAR(64) NULL,
            ipo_date VARCHAR(32) NULL,
            is_etf BOOLEAN NULL,
            is_actively_trading BOOLEAN NULL,
            is_adr BOOLEAN NULL,
            is_fund BOOLEAN NULL,
            profile_updated_at DATETIME NULL
        )
        """
        with self.client.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()

    def upsert_company(self, company: dict[str, Any]) -> None:
        """Speichert oder aktualisiert ein Unternehmensprofil."""
        sql = """
        INSERT INTO companies (
            symbol, company_name, market_cap, price, currency, cik, isin, cusip,
            exchange, exchange_full_name, industry, sector, country, website,
            description, ceo, full_time_employees, ipo_date, is_etf,
            is_actively_trading, is_adr, is_fund, profile_updated_at
        ) VALUES (
            %(symbol)s, %(company_name)s, %(market_cap)s, %(price)s, %(currency)s, %(cik)s, %(isin)s, %(cusip)s,
            %(exchange)s, %(exchange_full_name)s, %(industry)s, %(sector)s, %(country)s, %(website)s,
            %(description)s, %(ceo)s, %(full_time_employees)s, %(ipo_date)s, %(is_etf)s,
            %(is_actively_trading)s, %(is_adr)s, %(is_fund)s, %(profile_updated_at)s
        )
        ON DUPLICATE KEY UPDATE
            company_name=VALUES(company_name),
            market_cap=VALUES(market_cap),
            price=VALUES(price),
            sector=VALUES(sector),
            country=VALUES(country),
            profile_updated_at=VALUES(profile_updated_at)
        """
        with self.client.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, company)
            conn.commit()

    def fetch_company(self, symbol: str) -> pd.DataFrame:
        """Liefert ein Unternehmensprofil nach Symbol."""
        with self.client.connect() as conn:
            return pd.read_sql("SELECT * FROM companies WHERE symbol = %s", conn, params=(symbol,))

    def fetch_all_symbols(self) -> list[str]:
        """Liefert vorhandene Tickersymbole."""
        with self.client.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT symbol FROM companies ORDER BY symbol")
                return [row[0] for row in cur.fetchall()]

    def count_all(self) -> int:
        """Liefert die Anzahl gespeicherter Firmenprofile."""
        with self.client.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM companies")
                return int(cur.fetchone()[0])
