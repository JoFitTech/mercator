"""Schlanke Repository-Schicht für MySQL-Zugriffe in FinanzPort Academic."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.db.mysql_client import MySqlClient


class CompanyRepository:
    """Kapselt CRUD-nahe Zugriffe auf die Tabelle ``companies``."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        """Wandelt Cursor-Resultsets in Listen aus Dictionaries um.

        Args:
            cursor: MySQL-Cursor mit gesetzter ``description``.
            rows: Ergebniszeilen als Tupel.

        Returns:
            Liste zeilenweiser Dictionaries.
        """

        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    def upsert_company(self, company: dict[str, Any]) -> None:
        """Speichert oder aktualisiert ein Unternehmensprofil per Upsert.

        Args:
            company: Feldwerte entsprechend dem ``companies``-Schema.

        Returns:
            None.
        """

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
                company_name = VALUES(company_name),
                market_cap = VALUES(market_cap),
                price = VALUES(price),
                currency = VALUES(currency),
                cik = VALUES(cik),
                isin = VALUES(isin),
                cusip = VALUES(cusip),
                exchange = VALUES(exchange),
                exchange_full_name = VALUES(exchange_full_name),
                industry = VALUES(industry),
                sector = VALUES(sector),
                country = VALUES(country),
                website = VALUES(website),
                description = VALUES(description),
                ceo = VALUES(ceo),
                full_time_employees = VALUES(full_time_employees),
                ipo_date = VALUES(ipo_date),
                is_etf = VALUES(is_etf),
                is_actively_trading = VALUES(is_actively_trading),
                is_adr = VALUES(is_adr),
                is_fund = VALUES(is_fund),
                profile_updated_at = VALUES(profile_updated_at)
        """
        params = {
            "symbol": company.get("symbol"),
            "company_name": company.get("company_name"),
            "market_cap": company.get("market_cap"),
            "price": company.get("price"),
            "currency": company.get("currency"),
            "cik": company.get("cik"),
            "isin": company.get("isin"),
            "cusip": company.get("cusip"),
            "exchange": company.get("exchange"),
            "exchange_full_name": company.get("exchange_full_name"),
            "industry": company.get("industry"),
            "sector": company.get("sector"),
            "country": company.get("country"),
            "website": company.get("website"),
            "description": company.get("description"),
            "ceo": company.get("ceo"),
            "full_time_employees": company.get("full_time_employees"),
            "ipo_date": company.get("ipo_date"),
            "is_etf": company.get("is_etf"),
            "is_actively_trading": company.get("is_actively_trading"),
            "is_adr": company.get("is_adr"),
            "is_fund": company.get("is_fund"),
            "profile_updated_at": company.get("profile_updated_at"),
        }

        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
            conn.commit()

    def get_company_by_symbol(self, symbol: str) -> dict[str, Any] | None:
        """Lädt genau ein Unternehmensprofil über das Symbol.

        Args:
            symbol: Börsenkürzel des Unternehmens.

        Returns:
            Gefundenes Profil oder ``None``.
        """

        query = "SELECT * FROM companies WHERE symbol = %s"
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (symbol,))
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._rows_to_dicts(cursor, [row])[0]

    def list_companies(self, limit: int = 100) -> list[dict[str, Any]]:
        """Lädt eine limitierte Liste gespeicherter Unternehmen.

        Args:
            limit: Maximale Anzahl zurückgegebener Zeilen.

        Returns:
            Liste von Unternehmens-Dictionaries.
        """

        query = "SELECT * FROM companies ORDER BY symbol ASC LIMIT %s"
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()
                return self._rows_to_dicts(cursor, rows)

    def count_all(self) -> int:
        """Liefert die Anzahl gespeicherter Unternehmen."""

        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM companies")
                result = cursor.fetchone()
                return int(result[0]) if result else 0


class InsiderTradeRepository:
    """Kapselt CRUD-nahe Zugriffe auf die Tabelle ``insider_trades``."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        """Wandelt Cursor-Resultsets in Listen aus Dictionaries um.

        Args:
            cursor: MySQL-Cursor mit gesetzter ``description``.
            rows: Ergebniszeilen als Tupel.

        Returns:
            Liste zeilenweiser Dictionaries.
        """

        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    def upsert_trade(self, trade: dict[str, Any]) -> None:
        """Speichert oder aktualisiert genau einen Insider-Trade.

        Args:
            trade: Feldwerte entsprechend dem ``insider_trades``-Schema.

        Returns:
            None.
        """

        sql = """
            INSERT INTO insider_trades (
                symbol, filing_date, transaction_date, reporting_cik, company_cik,
                reporting_name, type_of_owner, transaction_type, acquisition_or_disposition,
                direct_or_indirect, form_type, security_name, qty, price,
                trade_value_estimated, gate_status, source_url, dedupe_key, fetched_at
            ) VALUES (
                %(symbol)s, %(filing_date)s, %(transaction_date)s, %(reporting_cik)s, %(company_cik)s,
                %(reporting_name)s, %(type_of_owner)s, %(transaction_type)s, %(acquisition_or_disposition)s,
                %(direct_or_indirect)s, %(form_type)s, %(security_name)s, %(qty)s, %(price)s,
                %(trade_value_estimated)s, %(gate_status)s, %(source_url)s, %(dedupe_key)s, %(fetched_at)s
            )
            ON DUPLICATE KEY UPDATE
                symbol = VALUES(symbol),
                filing_date = VALUES(filing_date),
                transaction_date = VALUES(transaction_date),
                reporting_cik = VALUES(reporting_cik),
                company_cik = VALUES(company_cik),
                reporting_name = VALUES(reporting_name),
                type_of_owner = VALUES(type_of_owner),
                transaction_type = VALUES(transaction_type),
                acquisition_or_disposition = VALUES(acquisition_or_disposition),
                direct_or_indirect = VALUES(direct_or_indirect),
                form_type = VALUES(form_type),
                security_name = VALUES(security_name),
                qty = VALUES(qty),
                price = VALUES(price),
                trade_value_estimated = VALUES(trade_value_estimated),
                gate_status = VALUES(gate_status),
                source_url = VALUES(source_url),
                fetched_at = VALUES(fetched_at)
        """
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, trade)
            conn.commit()

    def upsert_trades(self, trades: list[dict[str, Any]]) -> int:
        """Speichert oder aktualisiert mehrere Insider-Trades im Batch.

        Args:
            trades: Liste von Trade-Dictionaries.

        Returns:
            Anzahl verarbeiteter Trades.
        """

        if not trades:
            return 0

        sql = """
            INSERT INTO insider_trades (
                symbol, filing_date, transaction_date, reporting_cik, company_cik,
                reporting_name, type_of_owner, transaction_type, acquisition_or_disposition,
                direct_or_indirect, form_type, security_name, qty, price,
                trade_value_estimated, gate_status, source_url, dedupe_key, fetched_at
            ) VALUES (
                %(symbol)s, %(filing_date)s, %(transaction_date)s, %(reporting_cik)s, %(company_cik)s,
                %(reporting_name)s, %(type_of_owner)s, %(transaction_type)s, %(acquisition_or_disposition)s,
                %(direct_or_indirect)s, %(form_type)s, %(security_name)s, %(qty)s, %(price)s,
                %(trade_value_estimated)s, %(gate_status)s, %(source_url)s, %(dedupe_key)s, %(fetched_at)s
            )
            ON DUPLICATE KEY UPDATE
                symbol = VALUES(symbol),
                filing_date = VALUES(filing_date),
                transaction_date = VALUES(transaction_date),
                reporting_cik = VALUES(reporting_cik),
                company_cik = VALUES(company_cik),
                reporting_name = VALUES(reporting_name),
                type_of_owner = VALUES(type_of_owner),
                transaction_type = VALUES(transaction_type),
                acquisition_or_disposition = VALUES(acquisition_or_disposition),
                direct_or_indirect = VALUES(direct_or_indirect),
                form_type = VALUES(form_type),
                security_name = VALUES(security_name),
                qty = VALUES(qty),
                price = VALUES(price),
                trade_value_estimated = VALUES(trade_value_estimated),
                gate_status = VALUES(gate_status),
                source_url = VALUES(source_url),
                fetched_at = VALUES(fetched_at)
        """
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, trades)
            conn.commit()
        return len(trades)

    def get_trade_by_dedupe_key(self, dedupe_key: str) -> dict[str, Any] | None:
        """Lädt genau einen Trade über dessen Deduplizierungsschlüssel.

        Args:
            dedupe_key: Eindeutiger SHA-basierter Schlüssel.

        Returns:
            Gefundener Trade oder ``None``.
        """

        query = "SELECT * FROM insider_trades WHERE dedupe_key = %s"
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (dedupe_key,))
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._rows_to_dicts(cursor, [row])[0]

    def list_latest_trades(self, limit: int = 100) -> list[dict[str, Any]]:
        """Lädt die neuesten Trades nach Filing- und Erfassungsdatum.

        Args:
            limit: Maximale Anzahl zurückgegebener Zeilen.

        Returns:
            Liste von Trade-Dictionaries.
        """

        query = """
            SELECT *
            FROM insider_trades
            ORDER BY filing_date DESC, fetched_at DESC, id DESC
            LIMIT %s
        """
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()
                return self._rows_to_dicts(cursor, rows)

    def list_trades_by_symbol(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        """Lädt Trades für ein einzelnes Symbol.

        Args:
            symbol: Börsenkürzel.
            limit: Maximale Anzahl zurückgegebener Zeilen.

        Returns:
            Liste von Trade-Dictionaries.
        """

        query = """
            SELECT *
            FROM insider_trades
            WHERE symbol = %s
            ORDER BY filing_date DESC, fetched_at DESC, id DESC
            LIMIT %s
        """
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (symbol, limit))
                rows = cursor.fetchall()
                return self._rows_to_dicts(cursor, rows)

    def fetch_trades(self, filters: dict[str, Any] | None = None, limit: int = 500) -> pd.DataFrame:
        """Liefert Trades als DataFrame für bestehende Analyse- und UI-Pfade.

        Args:
            filters: Optionale Filter auf Trade- und Company-Felder.
            limit: Zeilenlimit.

        Returns:
            DataFrame mit Trade- und optionalen Company-Feldern.
        """

        filters = filters or {}
        clauses: list[str] = []
        params: list[Any] = []

        if filters.get("symbol"):
            clauses.append("t.symbol = %s")
            params.append(filters["symbol"])
        if filters.get("transaction_type"):
            clauses.append("t.transaction_type = %s")
            params.append(filters["transaction_type"])
        if filters.get("gate_status"):
            clauses.append("t.gate_status = %s")
            params.append(filters["gate_status"])
        if filters.get("sector"):
            clauses.append("c.sector = %s")
            params.append(filters["sector"])
        if filters.get("country"):
            clauses.append("c.country = %s")
            params.append(filters["country"])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
            SELECT t.*, c.company_name, c.sector, c.country
            FROM insider_trades t
            LEFT JOIN companies c ON c.symbol = t.symbol
            {where_sql}
            ORDER BY t.filing_date DESC, t.id DESC
            LIMIT %s
        """
        params.append(limit)

        with self._client.connection() as conn:
            return pd.read_sql(query, conn, params=params)

    def count_all(self) -> int:
        """Liefert die Anzahl gespeicherter Insider-Trades."""

        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM insider_trades")
                result = cursor.fetchone()
                return int(result[0]) if result else 0


class CompanyMySqlRepository(CompanyRepository):
    """Kompatibilitätsklasse für bestehende Aufrufe im Projekt."""

    def fetch_company(self, symbol: str) -> pd.DataFrame:
        """Liefert ein Unternehmensprofil als DataFrame für Altpfade."""

        data = self.get_company_by_symbol(symbol)
        return pd.DataFrame([data]) if data else pd.DataFrame()

    def fetch_all_symbols(self) -> list[str]:
        """Liefert alle verfügbaren Symbole für bestehende Aufrufe."""

        return [row["symbol"] for row in self.list_companies(limit=100000)]


class InsiderTradeMySqlRepository(InsiderTradeRepository):
    """Kompatibilitätsklasse für bestehende Aufrufe im Projekt."""
