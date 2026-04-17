"""Schlanke Repository-Schicht für MySQL-Zugriffe in Mercator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from src.domain_rules import normalize_symbol, sanitize_symbol_options
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
                company_key, company_cik, current_symbol, company_name, profile_status, profile_reason, first_seen_at, last_seen_at, market_cap, price, currency, isin, cusip,
                exchange, exchange_full_name, industry, sector,
                sector_raw, sector_normalized, sector_source, sector_resolution_method, sector_resolution_status,
                profile_enriched_at, profile_provider,
                country, website,
                description, ceo, full_time_employees, ipo_date, is_etf,
                is_actively_trading, is_adr, is_fund, profile_updated_at, source_system,
                trade_republic_universe_status, trade_republic_match_method, trade_republic_match_confidence,
                trade_republic_source_refreshed_at, trade_republic_reference_isin, trade_republic_reference_name,
                sync_version, created_at, updated_at
            ) VALUES (
                %(company_key)s, %(company_cik)s, %(current_symbol)s, %(company_name)s, %(profile_status)s, %(profile_reason)s, %(first_seen_at)s, %(last_seen_at)s, %(market_cap)s, %(price)s, %(currency)s, %(isin)s, %(cusip)s,
                %(exchange)s, %(exchange_full_name)s, %(industry)s, %(sector)s,
                %(sector_raw)s, %(sector_normalized)s, %(sector_source)s, %(sector_resolution_method)s, %(sector_resolution_status)s,
                %(profile_enriched_at)s, %(profile_provider)s,
                %(country)s, %(website)s,
                %(description)s, %(ceo)s, %(full_time_employees)s, %(ipo_date)s, %(is_etf)s,
                %(is_actively_trading)s, %(is_adr)s, %(is_fund)s, %(profile_updated_at)s, %(source_system)s,
                %(trade_republic_universe_status)s, %(trade_republic_match_method)s, %(trade_republic_match_confidence)s,
                %(trade_republic_source_refreshed_at)s, %(trade_republic_reference_isin)s, %(trade_republic_reference_name)s,
                %(sync_version)s, %(created_at)s, %(updated_at)s
            )
            ON DUPLICATE KEY UPDATE
                company_cik = COALESCE(VALUES(company_cik), company_cik),
                current_symbol = COALESCE(VALUES(current_symbol), current_symbol),
                company_name = COALESCE(VALUES(company_name), company_name),
                profile_status = CASE
                    WHEN VALUES(profile_status) = 'NOT_REQUESTED' AND profile_status = 'FETCHED' THEN profile_status
                    ELSE VALUES(profile_status)
                END,
                profile_reason = CASE
                    WHEN VALUES(profile_status) = 'NOT_REQUESTED' AND profile_status = 'FETCHED' THEN profile_reason
                    ELSE VALUES(profile_reason)
                END,
                first_seen_at = COALESCE(first_seen_at, VALUES(first_seen_at)),
                last_seen_at = COALESCE(VALUES(last_seen_at), last_seen_at),
                market_cap = VALUES(market_cap),
                price = VALUES(price),
                currency = VALUES(currency),
                isin = VALUES(isin),
                cusip = VALUES(cusip),
                exchange = VALUES(exchange),
                exchange_full_name = VALUES(exchange_full_name),
                industry = VALUES(industry),
                sector = VALUES(sector),
                sector_raw = VALUES(sector_raw),
                sector_normalized = VALUES(sector_normalized),
                sector_source = VALUES(sector_source),
                sector_resolution_method = VALUES(sector_resolution_method),
                sector_resolution_status = VALUES(sector_resolution_status),
                profile_enriched_at = VALUES(profile_enriched_at),
                profile_provider = VALUES(profile_provider),
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
                profile_updated_at = VALUES(profile_updated_at),
                source_system = VALUES(source_system),
                trade_republic_universe_status = VALUES(trade_republic_universe_status),
                trade_republic_match_method = VALUES(trade_republic_match_method),
                trade_republic_match_confidence = VALUES(trade_republic_match_confidence),
                trade_republic_source_refreshed_at = VALUES(trade_republic_source_refreshed_at),
                trade_republic_reference_isin = VALUES(trade_republic_reference_isin),
                trade_republic_reference_name = VALUES(trade_republic_reference_name),
                sync_version = VALUES(sync_version),
                created_at = COALESCE(created_at, VALUES(created_at)),
                updated_at = VALUES(updated_at)
        """
        inferred_created_at = (
            company.get("created_at")
            or company.get("first_seen_at")
            or company.get("profile_updated_at")
            or company.get("last_seen_at")
        )
        inferred_updated_at = (
            company.get("updated_at")
            or company.get("last_seen_at")
            or company.get("profile_updated_at")
            or company.get("first_seen_at")
            or inferred_created_at
        )
        params = {
            "company_key": company.get("company_key"),
            "company_cik": company.get("company_cik"),
            "current_symbol": company.get("current_symbol"),
            "company_name": company.get("company_name"),
            "market_cap": company.get("market_cap"),
            "price": company.get("price"),
            "currency": company.get("currency"),
            "profile_status": company.get("profile_status", "NOT_REQUESTED"),
            "profile_reason": company.get("profile_reason"),
            "first_seen_at": company.get("first_seen_at"),
            "last_seen_at": company.get("last_seen_at"),
            "isin": company.get("isin"),
            "cusip": company.get("cusip"),
            "exchange": company.get("exchange"),
            "exchange_full_name": company.get("exchange_full_name"),
            "industry": company.get("industry"),
            "sector": company.get("sector"),
            "sector_raw": company.get("sector_raw"),
            "sector_normalized": company.get("sector_normalized"),
            "sector_source": company.get("sector_source"),
            "sector_resolution_method": company.get("sector_resolution_method"),
            "sector_resolution_status": company.get("sector_resolution_status", "UNRESOLVED"),
            "profile_enriched_at": company.get("profile_enriched_at"),
            "profile_provider": company.get("profile_provider"),
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
            "source_system": company.get("source_system", "fmp"),
            "trade_republic_universe_status": company.get("trade_republic_universe_status", "UNKNOWN"),
            "trade_republic_match_method": company.get("trade_republic_match_method", "NONE"),
            "trade_republic_match_confidence": company.get("trade_republic_match_confidence", "LOW"),
            "trade_republic_source_refreshed_at": company.get("trade_republic_source_refreshed_at"),
            "trade_republic_reference_isin": company.get("trade_republic_reference_isin"),
            "trade_republic_reference_name": company.get("trade_republic_reference_name"),
            "sync_version": int(company.get("sync_version") or 1),
            "created_at": inferred_created_at,
            "updated_at": inferred_updated_at,
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

        normalized = str(symbol or "").strip().upper()
        query = "SELECT * FROM companies WHERE current_symbol = %s OR company_key = %s LIMIT 1"
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (normalized, normalized))
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._rows_to_dicts(cursor, [row])[0]

    def get_company_by_current_symbol(self, symbol: str) -> dict[str, Any] | None:
        """Lädt ein Unternehmensprofil explizit über den fachlichen Business-Key `current_symbol`."""

        normalized = str(symbol or "").strip().upper()
        if not normalized:
            return None
        query = "SELECT * FROM companies WHERE current_symbol = %s LIMIT 1"
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (normalized,))
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._rows_to_dicts(cursor, [row])[0]

    def list_companies(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Lädt eine limitierte Liste gespeicherter Unternehmen.

        Args:
            limit: Maximale Anzahl zurückgegebener Zeilen.
            offset: Anzahl zu überspringender Zeilen für Paging.

        Returns:
            Liste von Unternehmens-Dictionaries.
        """

        query = "SELECT * FROM companies ORDER BY COALESCE(current_symbol, company_key) ASC LIMIT %s OFFSET %s"
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit, offset))
                rows = cursor.fetchall()
                return self._rows_to_dicts(cursor, rows)

    def count_all(self) -> int:
        """Liefert die Anzahl gespeicherter Unternehmen."""

        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM companies")
                result = cursor.fetchone()
                return int(result[0]) if result else 0

    def get_max_updated_at(self) -> str | None:
        """Liefert den neuesten Zeitstempel aus der Spalte ``updated_at``."""
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT MAX(updated_at) FROM companies")
                result = cursor.fetchone()
                return str(result[0]) if result and result[0] is not None else None


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
                company_key, symbol_at_trade, filing_date, transaction_date, reporting_cik, company_cik,
                reporting_name, type_of_owner, transaction_type, acquisition_or_disposition,
                direct_or_indirect, form_type, security_name, qty, price,
                trade_value_estimated, validation_status, gate_status, gate_reason, score, score_class,
                profile_status, profile_reason, source_url,
                trade_republic_universe_status, trade_republic_match_method, trade_republic_match_confidence,
                trade_republic_source_refreshed_at, trade_republic_reference_isin, trade_republic_reference_name,
                dedupe_key, fetched_at
            ) VALUES (
                %(company_key)s, %(symbol_at_trade)s, %(filing_date)s, %(transaction_date)s, %(reporting_cik)s, %(company_cik)s,
                %(reporting_name)s, %(type_of_owner)s, %(transaction_type)s, %(acquisition_or_disposition)s,
                %(direct_or_indirect)s, %(form_type)s, %(security_name)s, %(qty)s, %(price)s,
                %(trade_value_estimated)s, %(validation_status)s, %(gate_status)s, %(gate_reason)s, %(score)s, %(score_class)s,
                %(profile_status)s, %(profile_reason)s, %(source_url)s,
                %(trade_republic_universe_status)s, %(trade_republic_match_method)s, %(trade_republic_match_confidence)s,
                %(trade_republic_source_refreshed_at)s, %(trade_republic_reference_isin)s, %(trade_republic_reference_name)s,
                %(dedupe_key)s, %(fetched_at)s
            )
            ON DUPLICATE KEY UPDATE
                company_key = VALUES(company_key),
                symbol_at_trade = VALUES(symbol_at_trade),
                filing_date = VALUES(filing_date),
                transaction_date = VALUES(transaction_date),
                reporting_cik = VALUES(reporting_cik),
                company_cik = VALUES(company_cik),
                reporting_name = VALUES(reporting_name),
                type_of_owner = VALUES(type_of_owner),
                transaction_type = VALUES(transaction_type),
                direct_or_indirect = VALUES(direct_or_indirect),
                form_type = VALUES(form_type),
                security_name = VALUES(security_name),
                qty = VALUES(qty),
                price = VALUES(price),
                trade_value_estimated = VALUES(trade_value_estimated),
                validation_status = VALUES(validation_status),
                gate_status = VALUES(gate_status),
                gate_reason = VALUES(gate_reason),
                score = VALUES(score),
                score_class = VALUES(score_class),
                profile_status = VALUES(profile_status),
                profile_reason = VALUES(profile_reason),
                source_url = VALUES(source_url),
                trade_republic_universe_status = VALUES(trade_republic_universe_status),
                trade_republic_match_method = VALUES(trade_republic_match_method),
                trade_republic_match_confidence = VALUES(trade_republic_match_confidence),
                trade_republic_source_refreshed_at = VALUES(trade_republic_source_refreshed_at),
                trade_republic_reference_isin = VALUES(trade_republic_reference_isin),
                trade_republic_reference_name = VALUES(trade_republic_reference_name),
                fetched_at = VALUES(fetched_at)
        """
        fields = [
            "company_key", "symbol_at_trade", "filing_date", "transaction_date", "reporting_cik", "company_cik",
            "reporting_name", "type_of_owner", "transaction_type", "acquisition_or_disposition",
            "direct_or_indirect", "form_type", "security_name", "qty", "price",
            "trade_value_estimated", "validation_status", "gate_status", "gate_reason", "score", "score_class",
            "profile_status", "profile_reason", "source_url",
            "trade_republic_universe_status", "trade_republic_match_method", "trade_republic_match_confidence",
            "trade_republic_source_refreshed_at", "trade_republic_reference_isin", "trade_republic_reference_name",
            "dedupe_key", "fetched_at"
        ]
        params = {k: trade.get(k) for k in fields}
        params["score"] = trade.get("score", trade.get("score_value"))

        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
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
                company_key, symbol_at_trade, filing_date, transaction_date, reporting_cik, company_cik,
                reporting_name, type_of_owner, transaction_type, acquisition_or_disposition,
                direct_or_indirect, form_type, security_name, qty, price,
                trade_value_estimated, validation_status, dashboard_valid, gate_status, gate_reason, score, score_class,
                profile_status, profile_reason, source_url, dedupe_key, fetched_at
            ) VALUES (
                %(company_key)s, %(symbol_at_trade)s, %(filing_date)s, %(transaction_date)s, %(reporting_cik)s, %(company_cik)s,
                %(reporting_name)s, %(type_of_owner)s, %(transaction_type)s, %(acquisition_or_disposition)s,
                %(direct_or_indirect)s, %(form_type)s, %(security_name)s, %(qty)s, %(price)s,
                %(trade_value_estimated)s, %(validation_status)s, %(dashboard_valid)s, %(gate_status)s, %(gate_reason)s, %(score)s, %(score_class)s,
                %(profile_status)s, %(profile_reason)s, %(source_url)s, %(dedupe_key)s, %(fetched_at)s
            )
            ON DUPLICATE KEY UPDATE
                company_key = VALUES(company_key),
                symbol_at_trade = VALUES(symbol_at_trade),
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
                validation_status = VALUES(validation_status),
                dashboard_valid = VALUES(dashboard_valid),
                gate_status = VALUES(gate_status),
                gate_reason = VALUES(gate_reason),
                score = VALUES(score),
                score_class = VALUES(score_class),
                profile_status = VALUES(profile_status),
                profile_reason = VALUES(profile_reason),
                source_url = VALUES(source_url),
                fetched_at = VALUES(fetched_at)
        """
        fields = [
            "company_key", "symbol_at_trade", "filing_date", "transaction_date", "reporting_cik", "company_cik",
            "reporting_name", "type_of_owner", "transaction_type", "acquisition_or_disposition",
            "direct_or_indirect", "form_type", "security_name", "qty", "price",
            "trade_value_estimated", "validation_status", "dashboard_valid", "gate_status", "gate_reason", "score", "score_class",
            "profile_status", "profile_reason", "source_url", "dedupe_key", "fetched_at"
        ]
        batch_params = [
            {
                **{k: t.get(k) for k in fields},
                "score": t.get("score", t.get("score_value")),
            }
            for t in trades
        ]

        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, batch_params)
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

    def list_latest_trades(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Lädt die neuesten Trades nach Filing- und Erfassungsdatum.

        Args:
            limit: Maximale Anzahl zurückgegebener Zeilen.
            offset: Anzahl zu überspringender Zeilen für Paging.

        Returns:
            Liste von Trade-Dictionaries.
        """

        query = """
            SELECT *
            FROM insider_trades
            ORDER BY filing_date DESC, fetched_at DESC, id DESC
            LIMIT %s OFFSET %s
        """
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit, offset))
                rows = cursor.fetchall()
                return self._rows_to_dicts(cursor, rows)

    def list_trades_by_company_key(self, company_key: str, limit: int = 100) -> list[dict[str, Any]]:
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
            WHERE company_key = %s
            ORDER BY filing_date DESC, fetched_at DESC, id DESC
            LIMIT %s
        """
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (company_key, limit))
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
            clauses.append("t.symbol_at_trade = %s")
            params.append(str(filters["symbol"]).strip().upper())
        if filters.get("company_key"):
            clauses.append("t.company_key = %s")
            params.append(filters["company_key"])
        if filters.get("reporting_name"):
            clauses.append("t.reporting_name LIKE %s")
            params.append(f"%{filters['reporting_name']}%")
        if filters.get("acquisition_or_disposition"):
            clauses.append("t.acquisition_or_disposition = %s")
            params.append(filters["acquisition_or_disposition"])
        if filters.get("transaction_type"):
            clauses.append("t.transaction_type = %s")
            params.append(filters["transaction_type"])
        if filters.get("gate_status"):
            clauses.append("t.gate_status = %s")
            params.append(filters["gate_status"])
        if filters.get("validation_status"):
            clauses.append("t.validation_status = %s")
            params.append(filters["validation_status"])
        if filters.get("dashboard_valid") is not None:
            clauses.append("t.dashboard_valid = %s")
            params.append(1 if filters["dashboard_valid"] else 0)
        if filters.get("sector"):
            clauses.append("c.sector = %s")
            params.append(filters["sector"])
        if filters.get("date_from"):
            clauses.append("t.filing_date >= %s")
            params.append(filters["date_from"])
        if filters.get("date_to"):
            clauses.append("t.filing_date <= %s")
            params.append(filters["date_to"])
        if filters.get("min_score"):
            clauses.append("t.score >= %s")
            params.append(filters["min_score"])
        if filters.get("max_score"):
            clauses.append("t.score <= %s")
            params.append(filters["max_score"])
        if filters.get("country"):
            clauses.append("c.country = %s")
            params.append(filters["country"])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
            SELECT
                t.*,
                t.score AS score_value,
                c.company_name,
                c.sector,
                c.sector_raw,
                c.sector_normalized,
                c.sector_source,
                c.sector_resolution_method,
                c.sector_resolution_status,
                c.profile_enriched_at,
                c.profile_provider,
                c.country,
                c.market_cap,
                c.currency,
                c.exchange,
                c.exchange_full_name,
                c.industry,
                c.is_etf,
                c.is_actively_trading,
                c.is_adr,
                c.is_fund,
                c.current_symbol,
                c.source_system AS company_source_system,
                c.sync_version AS company_sync_version,
                c.trade_republic_universe_status AS company_trade_republic_universe_status,
                c.trade_republic_match_method AS company_trade_republic_match_method,
                c.trade_republic_match_confidence AS company_trade_republic_match_confidence,
                c.trade_republic_source_refreshed_at AS company_trade_republic_source_refreshed_at
            FROM insider_trades t
            LEFT JOIN companies c ON c.company_key = t.company_key
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

    def get_max_updated_at(self) -> str | None:
        """Liefert den neuesten Zeitstempel aus der Spalte ``updated_at``."""
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT MAX(updated_at) FROM insider_trades")
                result = cursor.fetchone()
                return str(result[0]) if result and result[0] is not None else None

    def get_extreme_dates(self) -> dict[str, str | None]:
        """Liefert das Datum des ältesten und neuesten Trades in der Datenbank."""
        query = "SELECT MIN(filing_date), MAX(filing_date) FROM insider_trades"
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                if result:
                    return {
                        "min_date": str(result[0]) if result[0] else None,
                        "max_date": str(result[1]) if result[1] else None
                    }
                return {"min_date": None, "max_date": None}


class CompanyMySqlRepository(CompanyRepository):
    """Kompatibilitätsklasse für bestehende Aufrufe im Projekt."""

    def fetch_company(self, symbol: str) -> pd.DataFrame:
        """Liefert ein Unternehmensprofil als DataFrame für Altpfade."""

        data = self.get_company_by_symbol(symbol)
        return pd.DataFrame([data]) if data else pd.DataFrame()

    def fetch_all_symbols(self) -> list[str]:
        """Liefert alle verfügbaren Symbole für bestehende Aufrufe."""
        query = """
            SELECT DISTINCT current_symbol
            FROM companies
            WHERE current_symbol IS NOT NULL AND TRIM(current_symbol) <> ''
            ORDER BY current_symbol
        """
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return sanitize_symbol_options(row[0] for row in cursor.fetchall())

    def fetch_all_sectors(self) -> list[str]:
        """Liefert alle verfügbaren Sektoren."""
        query = """
            SELECT DISTINCT sector
            FROM companies
            WHERE sector IS NOT NULL AND TRIM(sector) <> '' AND sector <> 'Unknown'
            ORDER BY sector
        """
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return [str(row[0]) for row in cursor.fetchall()]


class InsiderTradeMySqlRepository(InsiderTradeRepository):
    """Kompatibilitätsklasse für bestehende Aufrufe im Projekt."""

    def fetch_all_symbols(self) -> list[str]:
        """Liefert alle verfügbaren Symbole für bestehende Aufrufe.

        Root-Cause-Fix: `company_key` kann CIK-basierte Identifikatoren enthalten
        und darf nie in die Ticker-Auswahl gelangen.
        """
        query = """
            SELECT DISTINCT symbol_at_trade
            FROM insider_trades
            WHERE symbol_at_trade IS NOT NULL AND TRIM(symbol_at_trade) <> ''
            ORDER BY symbol_at_trade
        """
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                symbols: list[str] = []
                for row in cursor.fetchall():
                    symbol = normalize_symbol(row[0])
                    if symbol:
                        symbols.append(symbol)
                return sanitize_symbol_options(symbols)


class AppFilterSettingsRepository:
    """Persistiert UI-Filterzustände mit fachlichem Business-Key (scope + key)."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _encode_json(value: Any) -> str:
        """Serialisiert Werte stabil nach JSON für die JSON-Spalte."""

        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _decode_json(value: Any) -> Any:
        """Deserialisiert JSON-Werte defensiv aus MySQL/Pandas/Python-Objekten."""

        if value is None:
            return None
        if isinstance(value, (dict, list, int, float, bool)):
            return value
        return json.loads(str(value))

    def load(self, setting_scope: str, setting_key: str) -> Any:
        """Lädt genau einen gespeicherten Filterzustand."""

        query = """
            SELECT setting_value_json
            FROM app_filter_settings
            WHERE setting_scope = %s AND setting_key = %s
            LIMIT 1
        """
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (setting_scope, setting_key))
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._decode_json(row[0])

    def list_all(self, limit: int = 1000, offset: int = 0) -> list[dict[str, Any]]:
        """Liefert persistierte Filtereinstellungen für Sync und Diagnose."""

        query = "SELECT * FROM app_filter_settings ORDER BY setting_scope, setting_key LIMIT %s OFFSET %s"
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit, offset))
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
                return [dict(zip(columns, row, strict=False)) for row in rows]

    def get_by_business_key(self, setting_scope: str, setting_key: str) -> dict[str, Any] | None:
        """Lädt eine Filtereinstellung inklusive Metadaten über den Business-Key."""

        query = "SELECT * FROM app_filter_settings WHERE setting_scope = %s AND setting_key = %s LIMIT 1"
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (setting_scope, setting_key))
                row = cursor.fetchone()
                if row is None:
                    return None
                columns = [description[0] for description in cursor.description] if cursor.description else []
                return dict(zip(columns, row, strict=False))

    def upsert(self, payload: dict[str, Any]) -> None:
        """Speichert einen Filterzustand per Update-statt-Insert-Semantik via Upsert."""

        created_at = payload.get("created_at") or payload.get("updated_at") or datetime.now(timezone.utc)
        updated_at = payload.get("updated_at") or datetime.now(timezone.utc)
        sql = """
            INSERT INTO app_filter_settings (
                setting_scope, setting_key, setting_value_json, source_system, sync_version, created_at, updated_at
            ) VALUES (
                %(setting_scope)s, %(setting_key)s, %(setting_value_json)s, %(source_system)s, %(sync_version)s, %(created_at)s, %(updated_at)s
            )
            ON DUPLICATE KEY UPDATE
                setting_value_json = VALUES(setting_value_json),
                source_system = VALUES(source_system),
                sync_version = VALUES(sync_version),
                created_at = COALESCE(created_at, VALUES(created_at)),
                updated_at = VALUES(updated_at)
        """
        params = {
            "setting_scope": payload.get("setting_scope"),
            "setting_key": payload.get("setting_key"),
            "setting_value_json": self._encode_json(payload.get("setting_value_json")),
            "source_system": payload.get("source_system", "app"),
            "sync_version": int(payload.get("sync_version") or 1),
            "created_at": created_at,
            "updated_at": updated_at,
        }
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
            conn.commit()


class AppRuntimePreferencesRepository:
    """Persistiert allgemeine Laufzeitpräferenzen mit Business-Key `preference_key`."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _encode_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _decode_json(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (dict, list, int, float, bool)):
            return value
        return json.loads(str(value))

    def load(self, preference_key: str) -> Any:
        """Lädt genau eine gespeicherte Laufzeitpräferenz."""

        query = "SELECT preference_value_json FROM app_runtime_preferences WHERE preference_key = %s LIMIT 1"
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (preference_key,))
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._decode_json(row[0])

    def list_all(self, limit: int = 1000, offset: int = 0) -> list[dict[str, Any]]:
        """Liefert alle Preferences für Sync und Diagnose."""

        query = "SELECT * FROM app_runtime_preferences ORDER BY preference_key LIMIT %s OFFSET %s"
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit, offset))
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
                return [dict(zip(columns, row, strict=False)) for row in rows]

    def get_by_business_key(self, preference_key: str) -> dict[str, Any] | None:
        """Lädt eine Preference inklusive Metadaten über den Business-Key."""

        query = "SELECT * FROM app_runtime_preferences WHERE preference_key = %s LIMIT 1"
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (preference_key,))
                row = cursor.fetchone()
                if row is None:
                    return None
                columns = [description[0] for description in cursor.description] if cursor.description else []
                return dict(zip(columns, row, strict=False))

    def upsert(self, payload: dict[str, Any]) -> None:
        """Speichert eine Preference per Update-statt-Insert-Semantik via Upsert."""

        created_at = payload.get("created_at") or payload.get("updated_at") or datetime.now(timezone.utc)
        updated_at = payload.get("updated_at") or datetime.now(timezone.utc)
        sql = """
            INSERT INTO app_runtime_preferences (
                preference_key, preference_value_json, source_system, sync_version, created_at, updated_at
            ) VALUES (
                %(preference_key)s, %(preference_value_json)s, %(source_system)s, %(sync_version)s, %(created_at)s, %(updated_at)s
            )
            ON DUPLICATE KEY UPDATE
                preference_value_json = VALUES(preference_value_json),
                source_system = VALUES(source_system),
                sync_version = VALUES(sync_version),
                created_at = COALESCE(created_at, VALUES(created_at)),
                updated_at = VALUES(updated_at)
        """
        params = {
            "preference_key": payload.get("preference_key"),
            "preference_value_json": self._encode_json(payload.get("preference_value_json")),
            "source_system": payload.get("source_system", "app"),
            "sync_version": int(payload.get("sync_version") or 1),
            "created_at": created_at,
            "updated_at": updated_at,
        }
        with self._client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
            conn.commit()
