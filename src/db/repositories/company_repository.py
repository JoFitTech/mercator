"""Repository für Unternehmensdaten in MySQL."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from src.db.mysql_client import MySqlClient

class CompanyRepository:
    """Kapselt CRUD-nahe Zugriffe auf die Tabelle ``companies``."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        """Wandelt Cursor-Resultsets in Listen aus Dictionaries um."""
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    @staticmethod
    def _normalize_sector_resolution_status(raw_value: Any) -> str:
        """Garantiert einen gueltigen NOT-NULL-Status fuer das Companies-Schema."""

        value = "" if raw_value is None else str(raw_value).strip().upper()
        return value or "UNRESOLVED"

    def upsert_company(self, company: dict[str, Any]) -> None:
        """Speichert oder aktualisiert ein Unternehmensprofil per Upsert."""
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
                updated_at = VALUES(updated_at)
        """
        now = datetime.now(timezone.utc)
        params = {
            "company_key": company.get("company_key"),
            "company_cik": company.get("company_cik"),
            "current_symbol": company.get("current_symbol"),
            "company_name": company.get("company_name"),
            "profile_status": company.get("profile_status", "NOT_REQUESTED"),
            "profile_reason": company.get("profile_reason"),
            "first_seen_at": company.get("first_seen_at", now),
            "last_seen_at": company.get("last_seen_at", now),
            "market_cap": company.get("market_cap"),
            "price": company.get("price"),
            "currency": company.get("currency"),
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
            "sector_resolution_status": self._normalize_sector_resolution_status(
                company.get("sector_resolution_status")
            ),
            "profile_enriched_at": company.get("profile_enriched_at"),
            "profile_provider": company.get("profile_provider"),
            "country": company.get("country"),
            "website": company.get("website"),
            "description": company.get("description"),
            "ceo": company.get("ceo"),
            "full_time_employees": company.get("full_time_employees"),
            "ipo_date": company.get("ipo_date"),
            "is_etf": company.get("is_etf", False),
            "is_actively_trading": company.get("is_actively_trading", True),
            "is_adr": company.get("is_adr", False),
            "is_fund": company.get("is_fund", False),
            "profile_updated_at": company.get("profile_updated_at"),
            "source_system": company.get("source_system", "FMP"),
            "trade_republic_universe_status": company.get("trade_republic_universe_status", "UNKNOWN"),
            "trade_republic_match_method": company.get("trade_republic_match_method") or "NONE",
            "trade_republic_match_confidence": company.get("trade_republic_match_confidence") or "LOW",
            "trade_republic_source_refreshed_at": company.get("trade_republic_source_refreshed_at"),
            "trade_republic_reference_isin": company.get("trade_republic_reference_isin"),
            "trade_republic_reference_name": company.get("trade_republic_reference_name"),
            "sync_version": company.get("sync_version", 1),
            "created_at": company.get("created_at", now),
            "updated_at": company.get("updated_at", now),
        }
        self._client.execute(sql, params)

    def list_active_companies(self, limit: int = 1000, offset: int = 0) -> list[dict[str, Any]]:
        """Lädt aktive Unternehmen mit aggregierten Trade-Statistiken (trade_count, last_trade_date)."""
        sql = """
            SELECT
                c.current_symbol,
                c.company_name,
                c.sector,
                c.industry,
                c.market_cap,
                COALESCE(ts.trade_count, 0) AS trade_count,
                ts.last_trade_date
            FROM companies c
            LEFT JOIN (
                SELECT
                    t.company_key,
                    COUNT(*) AS trade_count,
                    MAX(t.transaction_date) AS last_trade_date
                FROM insider_trades t
                GROUP BY t.company_key
            ) ts ON ts.company_key = c.company_key
            WHERE c.is_actively_trading = 1
            ORDER BY COALESCE(ts.trade_count, 0) DESC, c.current_symbol ASC
            LIMIT %s OFFSET %s
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (limit, offset))
                rows = cursor.fetchall()
                return self._rows_to_dicts(cursor, rows)

    def get_company_by_symbol(self, symbol: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM companies WHERE company_key = %s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (symbol,))
                row = cursor.fetchone()
                if row:
                    return self._rows_to_dicts(cursor, [row])[0]
        return None

    def get_company_by_current_symbol(self, symbol: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM companies WHERE current_symbol = %s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (symbol,))
                row = cursor.fetchone()
                if row:
                    return self._rows_to_dicts(cursor, [row])[0]
        return None

    def list_companies(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        sql = "SELECT * FROM companies ORDER BY updated_at DESC LIMIT %s OFFSET %s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (limit, offset))
                rows = cursor.fetchall()
                return self._rows_to_dicts(cursor, rows)

    def count_all(self) -> int:
        sql = "SELECT COUNT(*) FROM companies"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                return result[0] if result else 0

    def get_max_updated_at(self) -> datetime | None:
        sql = "SELECT MAX(updated_at) FROM companies"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                return result[0] if result and result[0] else None

class CompanyMySqlRepository(CompanyRepository):
    def fetch_company(self, symbol: str) -> dict[str, Any] | None:
        return self.get_company_by_symbol(symbol)

    def fetch_all_symbols(self) -> list[str]:
        sql = "SELECT DISTINCT current_symbol FROM companies WHERE current_symbol IS NOT NULL"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                return [row[0] for row in rows]

    def fetch_all_sectors(self) -> list[str]:
        sql = "SELECT DISTINCT sector FROM companies WHERE sector IS NOT NULL AND sector != ''"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                return [row[0] for row in rows]
