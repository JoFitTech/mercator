"""Repository für Unternehmensdaten in MySQL."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from src.db.mysql_client import MySqlClient

class CompanyRepository:
    """Kapselt CRUD-nahe Zugriffe auf die Tabelle ``companies``."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client
        self._upsert_sql = """
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
        self._upsert_trade_stats_delta_sql = """
            INSERT INTO company_trade_stats (
                company_key, trade_count, buy_count, sell_count, last_trade_date, updated_at
            ) VALUES (
                %(company_key)s, %(trade_count_delta)s, %(buy_count_delta)s, %(sell_count_delta)s, %(last_trade_date)s, UTC_TIMESTAMP()
            )
            ON DUPLICATE KEY UPDATE
                trade_count = trade_count + VALUES(trade_count),
                buy_count = buy_count + VALUES(buy_count),
                sell_count = sell_count + VALUES(sell_count),
                last_trade_date = GREATEST(COALESCE(last_trade_date, VALUES(last_trade_date)), COALESCE(VALUES(last_trade_date), last_trade_date)),
                updated_at = UTC_TIMESTAMP()
        """

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

    def _build_company_params(self, company: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        return {
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

    def upsert_company(self, company: dict[str, Any]) -> None:
        """Speichert oder aktualisiert ein Unternehmensprofil per Upsert."""
        self._client.execute(self._upsert_sql, self._build_company_params(company))

    def upsert_companies(self, companies: list[dict[str, Any]]) -> int:
        if not companies:
            return 0
        params_batch = [self._build_company_params(company) for company in companies]
        self._client.execute_many(self._upsert_sql, params_batch)
        return len(params_batch)

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
            LEFT JOIN company_trade_stats ts ON ts.company_key = c.company_key
            WHERE c.is_actively_trading = 1
            ORDER BY COALESCE(ts.trade_count, 0) DESC, c.current_symbol ASC
            LIMIT %s OFFSET %s
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (limit, offset))
                rows = cursor.fetchall()
                return self._rows_to_dicts(cursor, rows)

    def count_active_companies(self, search_term: str | None = None) -> int:
        sql = "SELECT COUNT(*) FROM companies c WHERE c.is_actively_trading = 1"
        params: list[Any] = []
        if search_term:
            sql += " AND (c.company_name LIKE %s OR c.current_symbol LIKE %s)"
            like = f"%{search_term}%"
            params.extend([like, like])
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchone()
                return int(result[0]) if result else 0

    def list_active_companies_page(
        self,
        limit: int,
        offset: int,
        search_term: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                c.current_symbol,
                c.company_name,
                c.profile_status,
                c.sector,
                c.industry,
                c.market_cap,
                COALESCE(ts.trade_count, 0) AS trade_count,
                ts.last_trade_date
            FROM companies c
            LEFT JOIN company_trade_stats ts ON ts.company_key = c.company_key
            WHERE c.is_actively_trading = 1
        """
        params: list[Any] = []
        if search_term:
            sql += " AND (c.company_name LIKE %s OR c.current_symbol LIKE %s)"
            like = f"%{search_term}%"
            params.extend([like, like])
        sql += " ORDER BY COALESCE(ts.trade_count, 0) DESC, c.current_symbol ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return self._rows_to_dicts(cursor, rows)

    def upsert_trade_stats_deltas(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        normalized: list[dict[str, Any]] = []
        for row in rows:
            company_key = str(row.get("company_key") or "").strip()
            if not company_key:
                continue
            normalized.append(
                {
                    "company_key": company_key,
                    "trade_count_delta": int(row.get("trade_count_delta", 0) or 0),
                    "buy_count_delta": int(row.get("buy_count_delta", 0) or 0),
                    "sell_count_delta": int(row.get("sell_count_delta", 0) or 0),
                    "last_trade_date": row.get("last_trade_date"),
                }
            )
        if not normalized:
            return 0
        self._client.execute_many(self._upsert_trade_stats_delta_sql, normalized)
        return len(normalized)

    def get_companies_by_keys(self, company_keys: list[str]) -> dict[str, dict[str, Any]]:
        if not company_keys:
            return {}
        placeholders = ", ".join(["%s"] * len(company_keys))
        sql = f"SELECT * FROM companies WHERE company_key IN ({placeholders})"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, company_keys)
                rows = cursor.fetchall()
                as_dicts = self._rows_to_dicts(cursor, rows)
        return {str(row.get("company_key")): row for row in as_dicts if row.get("company_key")}

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

    def recompute_trade_stats_for_company_keys(self, company_keys: list[str]) -> int:
        """
        Rekalkuliert company_trade_stats für die gegebenen company_keys DETERMINISTISCH.

        Dies berechnet Statistiken direkt aus der insider_trades-Tabelle neu,
        anstatt Deltas zu verwenden. Dadurch wird verhindert, dass wiederholte
        Imports mit überlappenden Trades zu Overcounting führen.

        Args:
            company_keys: Liste der company_keys, deren Statistiken neu berechnet werden sollen.

        Returns:
            Anzahl der aktualisierten Einträge in company_trade_stats.
        """
        if not company_keys:
            return 0

        normalized_keys = sorted({str(key).strip() for key in company_keys if str(key).strip()})
        if not normalized_keys:
            return 0

        key_rows_sql = " UNION ALL ".join(["SELECT %s AS company_key"] * len(normalized_keys))
        recompute_sql = f"""
            INSERT INTO company_trade_stats (company_key, trade_count, buy_count, sell_count, last_trade_date, updated_at)
            SELECT
                k.company_key,
                COUNT(t.company_key) AS trade_count,
                SUM(CASE WHEN t.acquisition_or_disposition IN ('A', 'BUY') THEN 1 ELSE 0 END) AS buy_count,
                SUM(CASE WHEN t.acquisition_or_disposition IN ('D', 'SELL') THEN 1 ELSE 0 END) AS sell_count,
                MAX(t.transaction_date) AS last_trade_date,
                UTC_TIMESTAMP() AS updated_at
            FROM ({key_rows_sql}) k
            LEFT JOIN insider_trades t ON t.company_key = k.company_key
            GROUP BY k.company_key
            ON DUPLICATE KEY UPDATE
                trade_count = VALUES(trade_count),
                buy_count = VALUES(buy_count),
                sell_count = VALUES(sell_count),
                last_trade_date = VALUES(last_trade_date),
                updated_at = VALUES(updated_at)
        """

        self._client.execute(recompute_sql, normalized_keys)
        return len(normalized_keys)

class CompanyMySqlRepository(CompanyRepository):
    def list_profile_backfill_candidates(self, limit: int = 100) -> list[str]:
        sql = """
            SELECT DISTINCT c.current_symbol
            FROM companies c
            WHERE c.current_symbol IS NOT NULL
              AND c.current_symbol <> ''
              AND (
                    COALESCE(c.profile_status, 'NOT_REQUESTED') IN ('NOT_REQUESTED', 'FAILED')
                    OR COALESCE(c.sector_resolution_status, 'UNRESOLVED') = 'UNRESOLVED'
                    OR c.sector IS NULL OR TRIM(c.sector) = ''
                    OR LOWER(TRIM(COALESCE(c.sector, ''))) IN ('unknown', 'unknown / api2 fehlt', 'api2 fehlt/unknown', 'api2 fehlt', 'n/a')
                    OR c.market_cap IS NULL
              )
            ORDER BY COALESCE(c.last_seen_at, c.updated_at) DESC
            LIMIT %s
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (int(limit),))
                rows = cursor.fetchall()
                return [str(row[0]).strip().upper() for row in rows if row and row[0]]

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
