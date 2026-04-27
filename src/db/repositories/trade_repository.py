"""Repository für Insider-Trades in MySQL."""

from __future__ import annotations
from typing import Any
import pandas as pd
from src.db.mysql_client import MySqlClient

class InsiderTradeRepository:
    """Kapselt CRUD-nahe Zugriffe auf die Tabelle ``insider_trades``."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client
        self._upsert_sql = """
            INSERT INTO insider_trades (
                company_key, symbol_at_trade, filing_date, transaction_date, reporting_cik, company_cik,
                reporting_name, type_of_owner, transaction_type, acquisition_or_disposition,
                direct_or_indirect, form_type, security_name, normalized_instrument_type, transaction_code_class, qty, price,
                trade_value_estimated, trade_value, filing_age_days, company_name, market_cap, industry, cik, isin, cusip,
                avg_20d_volume, avg_20d_dollar_volume, sma_50, sma_200, momentum_3m, momentum_6m, technical_state, liquidity_state,
                core_insider_score, investability_score, execution_score, trade_republic_score, final_score, final_class, decision_status,
                validation_status, dashboard_valid, gate_status, gate_reason, score, score_class,
                profile_status, profile_reason, source_url,
                trade_republic_universe_status, trade_republic_match_method, trade_republic_match_confidence,
                trade_republic_source_refreshed_at, trade_republic_reference_isin, trade_republic_reference_name,
                tr_availability_state, tr_tradability_state, tr_match_confidence,
                dedupe_key, fetched_at
            ) VALUES (
                %(company_key)s, %(symbol_at_trade)s, %(filing_date)s, %(transaction_date)s, %(reporting_cik)s, %(company_cik)s,
                %(reporting_name)s, %(type_of_owner)s, %(transaction_type)s, %(acquisition_or_disposition)s,
                %(direct_or_indirect)s, %(form_type)s, %(security_name)s, %(normalized_instrument_type)s, %(transaction_code_class)s, %(qty)s, %(price)s,
                %(trade_value_estimated)s, %(trade_value)s, %(filing_age_days)s, %(company_name)s, %(market_cap)s, %(industry)s, %(cik)s, %(isin)s, %(cusip)s,
                %(avg_20d_volume)s, %(avg_20d_dollar_volume)s, %(sma_50)s, %(sma_200)s, %(momentum_3m)s, %(momentum_6m)s, %(technical_state)s, %(liquidity_state)s,
                %(core_insider_score)s, %(investability_score)s, %(execution_score)s, %(trade_republic_score)s, %(final_score)s, %(final_class)s, %(decision_status)s,
                %(validation_status)s, %(dashboard_valid)s, %(gate_status)s, %(gate_reason)s, %(score)s, %(score_class)s,
                %(profile_status)s, %(profile_reason)s, %(source_url)s,
                %(trade_republic_universe_status)s, %(trade_republic_match_method)s, %(trade_republic_match_confidence)s,
                %(trade_republic_source_refreshed_at)s, %(trade_republic_reference_isin)s, %(trade_republic_reference_name)s,
                %(tr_availability_state)s, %(tr_tradability_state)s, %(tr_match_confidence)s,
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
                acquisition_or_disposition = VALUES(acquisition_or_disposition),
                direct_or_indirect = VALUES(direct_or_indirect),
                form_type = VALUES(form_type),
                security_name = VALUES(security_name),
                normalized_instrument_type = VALUES(normalized_instrument_type),
                transaction_code_class = VALUES(transaction_code_class),
                qty = VALUES(qty),
                price = VALUES(price),
                trade_value_estimated = VALUES(trade_value_estimated),
                trade_value = VALUES(trade_value),
                filing_age_days = VALUES(filing_age_days),
                company_name = VALUES(company_name),
                market_cap = VALUES(market_cap),
                industry = VALUES(industry),
                cik = VALUES(cik),
                isin = VALUES(isin),
                cusip = VALUES(cusip),
                avg_20d_volume = VALUES(avg_20d_volume),
                avg_20d_dollar_volume = VALUES(avg_20d_dollar_volume),
                sma_50 = VALUES(sma_50),
                sma_200 = VALUES(sma_200),
                momentum_3m = VALUES(momentum_3m),
                momentum_6m = VALUES(momentum_6m),
                technical_state = VALUES(technical_state),
                liquidity_state = VALUES(liquidity_state),
                core_insider_score = VALUES(core_insider_score),
                investability_score = VALUES(investability_score),
                execution_score = VALUES(execution_score),
                trade_republic_score = VALUES(trade_republic_score),
                final_score = VALUES(final_score),
                final_class = VALUES(final_class),
                decision_status = VALUES(decision_status),
                validation_status = VALUES(validation_status),
                dashboard_valid = VALUES(dashboard_valid),
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
                tr_availability_state = VALUES(tr_availability_state),
                tr_tradability_state = VALUES(tr_tradability_state),
                tr_match_confidence = VALUES(tr_match_confidence),
                fetched_at = VALUES(fetched_at)
        """
        self._upsert_fields = [
            "company_key", "symbol_at_trade", "filing_date", "transaction_date", "reporting_cik", "company_cik",
            "reporting_name", "type_of_owner", "transaction_type", "acquisition_or_disposition",
            "direct_or_indirect", "form_type", "security_name", "normalized_instrument_type", "transaction_code_class", "qty", "price",
            "trade_value_estimated", "trade_value", "filing_age_days", "company_name", "market_cap", "industry", "cik", "isin", "cusip",
            "avg_20d_volume", "avg_20d_dollar_volume", "sma_50", "sma_200", "momentum_3m", "momentum_6m", "technical_state", "liquidity_state",
            "core_insider_score", "investability_score", "execution_score", "trade_republic_score", "final_score", "final_class", "decision_status",
            "validation_status", "dashboard_valid", "gate_status", "gate_reason", "score", "score_class",
            "profile_status", "profile_reason", "source_url",
            "trade_republic_universe_status", "trade_republic_match_method", "trade_republic_match_confidence",
            "trade_republic_source_refreshed_at", "trade_republic_reference_isin", "trade_republic_reference_name",
            "tr_availability_state", "tr_tradability_state", "tr_match_confidence",
            "dedupe_key", "fetched_at"
        ]

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        """Wandelt Cursor-Resultsets in Listen aus Dictionaries um."""
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    @staticmethod
    def _coerce_bool(value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
        return default

    def _build_trade_params(self, trade: dict[str, Any]) -> dict[str, Any]:
        params = {k: trade.get(k) for k in self._upsert_fields}
        params["score"] = trade.get("score", trade.get("score_value"))
        params["dashboard_valid"] = self._coerce_bool(trade.get("dashboard_valid"), default=False)
        params["trade_republic_universe_status"] = trade.get("trade_republic_universe_status") or "UNKNOWN"
        params["trade_republic_match_method"] = trade.get("trade_republic_match_method") or "NONE"
        params["trade_republic_match_confidence"] = trade.get("trade_republic_match_confidence") or "LOW"
        params["tr_availability_state"] = trade.get("tr_availability_state") or "UNKNOWN"
        params["tr_tradability_state"] = trade.get("tr_tradability_state") or "UNKNOWN"
        params["tr_match_confidence"] = trade.get("tr_match_confidence") or trade.get("trade_republic_match_confidence") or "LOW"
        return params

    def upsert_trade(self, trade: dict[str, Any]) -> None:
        """Speichert oder aktualisiert genau einen Insider-Trade."""
        self._client.execute(self._upsert_sql, self._build_trade_params(trade))

    def upsert_trades(self, trades: list[dict[str, Any]]) -> int:
        """Speichert oder aktualisiert mehrere Insider-Trades im Batch."""
        if not trades:
            return 0
        params_batch = [self._build_trade_params(t) for t in trades]
        self._client.execute_many(self._upsert_sql, params_batch)
        return len(params_batch)

    @staticmethod
    def _build_filter_sql(filters: dict[str, Any] | None = None, *, alias: str = "") -> tuple[list[str], list[Any]]:
        prefix = f"{alias}." if alias else ""
        conditions: list[str] = []
        params: list[Any] = []
        if not filters:
            return conditions, params
        if filters.get("dedupe_key"):
            conditions.append(f"{prefix}dedupe_key = %s")
            params.append(filters["dedupe_key"])
        if filters.get("date_from"):
            conditions.append(f"{prefix}transaction_date >= %s")
            params.append(filters["date_from"])
        if filters.get("date_to"):
            conditions.append(f"{prefix}transaction_date <= %s")
            params.append(filters["date_to"])
        if filters.get("symbol"):
            conditions.append(f"{prefix}symbol_at_trade LIKE %s")
            params.append(f"%{filters['symbol']}%")
        if filters.get("company_key"):
            conditions.append(f"{prefix}company_key = %s")
            params.append(filters["company_key"])
        if filters.get("reporting_name"):
            conditions.append(f"{prefix}reporting_name LIKE %s")
            params.append(f"%{filters['reporting_name']}%")
        if filters.get("gate_status"):
            conditions.append(f"{prefix}gate_status = %s")
            params.append(filters["gate_status"])
        if filters.get("validation_status"):
            conditions.append(f"{prefix}validation_status = %s")
            params.append(filters["validation_status"])
        if filters.get("acquisition_or_disposition"):
            conditions.append(f"{prefix}acquisition_or_disposition = %s")
            params.append(filters["acquisition_or_disposition"])
        min_score = filters.get("min_score")
        if min_score is not None and min_score > 0:
            conditions.append(f"{prefix}score >= %s")
            params.append(min_score)
        min_value = filters.get("min_value")
        if min_value is not None and min_value > 0:
            conditions.append(f"{prefix}trade_value_estimated >= %s")
            params.append(min_value)
        if filters.get("trade_republic_universe_status"):
            status = str(filters["trade_republic_universe_status"]).strip().upper()
            if status and status != "ALL":
                conditions.append(f"{prefix}trade_republic_universe_status = %s")
                params.append(status)
        if filters.get("dashboard_valid") is not None:
            conditions.append(f"{prefix}dashboard_valid = %s")
            params.append(1 if filters["dashboard_valid"] else 0)
        return conditions, params

    def get_trade_by_dedupe_key(self, dedupe_key: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM insider_trades WHERE dedupe_key = %s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (dedupe_key,))
                row = cursor.fetchone()
                if row:
                    return self._rows_to_dicts(cursor, [row])[0]
        return None

    def list_latest_trades(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        sql = "SELECT * FROM insider_trades ORDER BY transaction_date DESC, filing_date DESC LIMIT %s OFFSET %s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (limit, offset))
                rows = cursor.fetchall()
                return self._rows_to_dicts(cursor, rows)

    def list_trades_by_company_key(self, company_key: str, limit: int = 100) -> list[dict[str, Any]]:
        sql = "SELECT * FROM insider_trades WHERE company_key = %s ORDER BY transaction_date DESC LIMIT %s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (company_key, limit))
                rows = cursor.fetchall()
                return self._rows_to_dicts(cursor, rows)

    def fetch_trades(self, filters: dict[str, Any] | None = None, limit: int = 500) -> pd.DataFrame:
        """Lädt Trades mit vollständig parametrisierten Filtern.

        Unterstützte Filter-Keys:
        - ``dedupe_key``      → exakter Match auf Deduplizierungs-Schlüssel (für Detailansicht)
        - ``symbol``          → Tickerfeld ``symbol_at_trade`` (LIKE, case-insensitiv)
        - ``company_key``     → interner Unternehmensschlüssel (Exakt-Match, nur für interne Nutzung)
        - ``reporting_name``  → Name des Insiders (LIKE)
        - ``gate_status``     → Exakt-Match, z.B. "PASS" / "FAIL"
        - ``validation_status`` → Exakt-Match, z.B. "VALID"
        - ``acquisition_or_disposition`` → Exakt-Match, z.B. "A" / "D"
        - ``min_score``       → Mindestscore (>=), wird ignoriert wenn 0
        - ``trade_republic_universe_status`` → Exakt-Match
        - ``date_from``       → transaction_date >=
        - ``date_to``         → transaction_date <=
        - ``dashboard_valid`` → Boolean-Flag

        Anmerkung: Diese Methode liefert nur Trade-Felder. Für Company-Felder wie `sector`
        in Dashboard-Kontexten verwende `fetch_trades_enriched_with_company(...)`.
        """
        sql = "SELECT * FROM insider_trades"
        conditions, params = self._build_filter_sql(filters)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY transaction_date DESC, filing_date DESC LIMIT %s"
        params.append(limit)

        with self._client.get_connection() as conn:
            return pd.read_sql(sql, conn, params=params)

    def fetch_trades_enriched_with_company(self, filters: dict[str, Any] | None = None, limit: int = 500) -> pd.DataFrame:
        """Lädt Trades mit LEFT JOIN auf Company-Tabelle für Dashboard/Analyse-Kontexte.

        Liefert zusätzlich zu Trade-Feldern auch Company-Felder wie:
        - sector, industry, market_cap (für Dashboard-Aggregation)

        Unterstützt alle Filter aus `fetch_trades(...)`.
        """
        # Das SQL für Trades wird entsprechend mit Company-LEFT-JOIN aufgebaut
        sql = """
            SELECT 
                t.*,
                t.score AS score_value,
                c.sector AS company_sector,
                c.industry AS company_industry,
                c.market_cap AS company_market_cap
            FROM insider_trades t
            LEFT JOIN companies c ON t.company_key = c.company_key
        """
        conditions, params = self._build_filter_sql(filters, alias="t")

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY t.transaction_date DESC, t.filing_date DESC LIMIT %s"
        params.append(limit)

        with self._client.get_connection() as conn:
            return pd.read_sql(sql, conn, params=params)

    def count_all(self) -> int:
        sql = "SELECT COUNT(*) FROM insider_trades"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                return result[0] if result else 0

    def count_trades(self, filters: dict[str, Any] | None = None) -> int:
        sql = "SELECT COUNT(*) FROM insider_trades"
        conditions, params = self._build_filter_sql(filters)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchone()
                return int(result[0]) if result else 0

    def fetch_trades_page(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> pd.DataFrame:
        sql = "SELECT * FROM insider_trades"
        conditions, params = self._build_filter_sql(filters)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY transaction_date DESC, filing_date DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        with self._client.get_connection() as conn:
            return pd.read_sql(sql, conn, params=params)

    def get_max_updated_at(self) -> str | None:
        sql = "SELECT MAX(fetched_at) FROM insider_trades"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                return str(result[0]) if result and result[0] is not None else None

    def get_extreme_dates(self) -> dict[str, Any]:
        sql = "SELECT MIN(transaction_date), MAX(transaction_date) FROM insider_trades"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                if result:
                    return {"min_date": result[0], "max_date": result[1]}
        return {"min_date": None, "max_date": None}

    def fetch_dashboard_kpi_snapshot(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        conditions, params = self._build_filter_sql(filters, alias="t")
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT
                SUM(CASE WHEN (t.symbol_at_trade IS NOT NULL AND t.symbol_at_trade != '' AND t.price > 0 AND t.qty > 0 AND t.acquisition_or_disposition IN ('A', 'D', 'BUY', 'SELL')) THEN 1 ELSE 0 END) AS relevant_trades,
                COUNT(DISTINCT CASE WHEN (t.symbol_at_trade IS NOT NULL AND t.symbol_at_trade != '' AND t.price > 0 AND t.qty > 0 AND t.acquisition_or_disposition IN ('A', 'D', 'BUY', 'SELL')) THEN t.symbol_at_trade END) AS affected_companies,
                SUM(CASE WHEN t.acquisition_or_disposition IN ('A', 'BUY') THEN 1 ELSE 0 END) AS buy_count,
                SUM(CASE WHEN t.acquisition_or_disposition IN ('D', 'SELL') THEN 1 ELSE 0 END) AS sell_count,
                SUM(CASE WHEN t.acquisition_or_disposition IN ('A', 'BUY') THEN COALESCE(t.trade_value_estimated, 0) ELSE 0 END) AS buy_volume,
                SUM(CASE WHEN t.acquisition_or_disposition IN ('D', 'SELL') THEN COALESCE(t.trade_value_estimated, 0) ELSE 0 END) AS sell_volume,
                SUM(CASE WHEN UPPER(COALESCE(t.gate_status, '')) = 'PASS' THEN 1 ELSE 0 END) AS gate_passed_count,
                AVG(t.score) AS avg_score
            FROM insider_trades t
            {where_clause}
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone() or ()
        return {
            "relevant_trades": int(row[0] or 0) if len(row) > 0 else 0,
            "affected_companies": int(row[1] or 0) if len(row) > 1 else 0,
            "buy_count": int(row[2] or 0) if len(row) > 2 else 0,
            "sell_count": int(row[3] or 0) if len(row) > 3 else 0,
            "buy_volume": float(row[4] or 0.0) if len(row) > 4 else 0.0,
            "sell_volume": float(row[5] or 0.0) if len(row) > 5 else 0.0,
            "gate_passed_count": int(row[6] or 0) if len(row) > 6 else 0,
            "avg_score": float(row[7]) if len(row) > 7 and row[7] is not None else 0.0,
        }

    def fetch_dashboard_sector_distribution(self, filters: dict[str, Any] | None = None) -> pd.DataFrame:
        conditions, params = self._build_filter_sql(filters, alias="t")
        conditions.append("t.acquisition_or_disposition IN ('A', 'BUY', 'D', 'SELL')")
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT
                CASE WHEN t.acquisition_or_disposition IN ('A', 'BUY') THEN 'BUY' ELSE 'SELL' END AS direction,
                COALESCE(NULLIF(TRIM(c.sector), ''), 'Unknown / API2 fehlt') AS sector,
                COUNT(*) AS count,
                SUM(COALESCE(t.trade_value_estimated, 0)) AS volume
            FROM insider_trades t
            LEFT JOIN companies c ON t.company_key = c.company_key
            {where_clause}
            GROUP BY direction, sector
        """
        with self._client.get_connection() as conn:
            return pd.read_sql(sql, conn, params=params)

    def fetch_dashboard_top_trades(self, direction: str, filters: dict[str, Any] | None = None, limit: int = 5) -> pd.DataFrame:
        direction_token = "A" if direction.upper() == "BUY" else "D"
        conditions, params = self._build_filter_sql(filters, alias="t")
        conditions.append("t.acquisition_or_disposition IN (%s, %s)")
        params.extend([direction_token, direction.upper()])
        where_clause = f"WHERE {' AND '.join(conditions)}"
        sql = f"""
            SELECT
                NULL AS accumulation_group_id,
                t.dedupe_key,
                t.symbol_at_trade,
                t.reporting_name,
                CASE WHEN t.acquisition_or_disposition IN ('A', 'BUY') THEN 'BUY' ELSE 'SELL' END AS direction,
                COALESCE(t.trade_value_estimated, 0) AS accumulated_trade_value_estimated,
                t.transaction_date AS trade_date,
                t.transaction_date AS accumulation_start_date,
                t.transaction_date AS accumulation_end_date,
                t.gate_status,
                t.profile_status,
                COALESCE(NULLIF(TRIM(c.sector), ''), 'Unknown / API2 fehlt') AS sector,
                CASE
                    WHEN c.market_cap IS NULL THEN 'Unknown / API2 fehlt'
                    WHEN c.market_cap < 2000000000 THEN 'Small Cap (<2B)'
                    WHEN c.market_cap < 10000000000 THEN 'Mid Cap (2B-10B)'
                    ELSE 'Large Cap (>=10B)'
                END AS market_cap_bucket
            FROM insider_trades t
            LEFT JOIN companies c ON t.company_key = c.company_key
            {where_clause}
            ORDER BY COALESCE(t.trade_value_estimated, 0) DESC
            LIMIT %s
        """
        params.append(limit)
        with self._client.get_connection() as conn:
            return pd.read_sql(sql, conn, params=params)

    def fetch_dashboard_decision_snapshot(self, filters: dict[str, Any] | None = None) -> dict[str, int]:
        conditions, params = self._build_filter_sql(filters, alias="t")
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT
                SUM(CASE WHEN UPPER(COALESCE(t.decision_status, '')) = 'ACTIONABLE_BUY' THEN 1 ELSE 0 END) AS actionable_buys,
                SUM(CASE WHEN UPPER(COALESCE(t.decision_status, '')) = 'BUY_CANDIDATE' THEN 1 ELSE 0 END) AS buy_candidates,
                SUM(CASE WHEN UPPER(COALESCE(t.decision_status, '')) = 'WATCHLIST' THEN 1 ELSE 0 END) AS watchlist,
                SUM(CASE WHEN UPPER(COALESCE(t.decision_status, '')) = 'SELL_WARNING' THEN 1 ELSE 0 END) AS sell_warnings,
                SUM(CASE WHEN UPPER(COALESCE(t.tr_availability_state, '')) = 'NOT_FOUND' THEN 1 ELSE 0 END) AS tr_not_found,
                SUM(CASE WHEN UPPER(COALESCE(t.trade_republic_match_confidence, '')) IN ('LOW', 'UNKNOWN') THEN 1 ELSE 0 END) AS exchange_resolution_issues,
                COUNT(DISTINCT CASE WHEN UPPER(COALESCE(t.profile_status, '')) = 'FETCHED' THEN t.symbol_at_trade END) AS fetched_profiles_count,
                COUNT(DISTINCT CASE WHEN UPPER(COALESCE(t.profile_status, '')) <> 'FETCHED' THEN t.symbol_at_trade END) AS missing_profiles_count
            FROM insider_trades t
            {where_clause}
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone() or ()
        return {
            "actionable_buys": int(row[0] or 0) if len(row) > 0 else 0,
            "buy_candidates": int(row[1] or 0) if len(row) > 1 else 0,
            "watchlist": int(row[2] or 0) if len(row) > 2 else 0,
            "sell_warnings": int(row[3] or 0) if len(row) > 3 else 0,
            "tr_not_found": int(row[4] or 0) if len(row) > 4 else 0,
            "exchange_resolution_issues": int(row[5] or 0) if len(row) > 5 else 0,
            "fetched_profiles_count": int(row[6] or 0) if len(row) > 6 else 0,
            "missing_profiles_count": int(row[7] or 0) if len(row) > 7 else 0,
        }

    def fetch_dashboard_missing_data_summary(self, filters: dict[str, Any] | None = None, limit: int = 25) -> list[dict[str, Any]]:
        conditions, params = self._build_filter_sql(filters, alias="t")
        conditions.extend([
            "t.symbol_at_trade IS NOT NULL",
            "t.symbol_at_trade <> ''",
        ])
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT
                t.symbol_at_trade,
                MAX(CASE WHEN UPPER(COALESCE(t.profile_status, '')) <> 'FETCHED' THEN 1 ELSE 0 END) AS missing_profile,
                MAX(CASE WHEN COALESCE(NULLIF(TRIM(c.sector), ''), 'Unknown / API2 fehlt') = 'Unknown / API2 fehlt' THEN 1 ELSE 0 END) AS missing_sector,
                MAX(CASE WHEN c.market_cap IS NULL THEN 1 ELSE 0 END) AS missing_market_cap
            FROM insider_trades t
            LEFT JOIN companies c ON c.company_key = t.company_key
            {where_clause}
            GROUP BY t.symbol_at_trade
            HAVING missing_profile = 1 OR missing_sector = 1 OR missing_market_cap = 1
            ORDER BY t.symbol_at_trade ASC
            LIMIT %s
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, [*params, int(limit)])
                rows = cursor.fetchall()
        return [
            {
                "symbol_at_trade": row[0],
                "missing_profile": bool(row[1]),
                "missing_sector": bool(row[2]),
                "missing_market_cap": bool(row[3]),
            }
            for row in rows
            if row and row[0]
        ]

    def fetch_dashboard_last_update(self, filters: dict[str, Any] | None = None):
        conditions, params = self._build_filter_sql(filters, alias="t")
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT MAX(t.transaction_date) FROM insider_trades t {where_clause}"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
                return row[0] if row else None

    def fetch_dashboard_market_cap_distribution(self, filters: dict[str, Any] | None = None) -> pd.DataFrame:
        conditions, params = self._build_filter_sql(filters, alias="t")
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT
                CASE
                    WHEN c.market_cap IS NULL THEN 'Unknown / API2 fehlt'
                    WHEN c.market_cap < 2000000000 THEN 'Small Cap (<2B)'
                    WHEN c.market_cap < 10000000000 THEN 'Mid Cap (2B-10B)'
                    ELSE 'Large Cap (>=10B)'
                END AS bucket,
                COUNT(DISTINCT t.company_key) AS companies
            FROM insider_trades t
            LEFT JOIN companies c ON c.company_key = t.company_key
            {where_clause}
            GROUP BY bucket
        """
        with self._client.get_connection() as conn:
            return pd.read_sql(sql, conn, params=params)

    def get_dashboard_state_token(self) -> str:
        sql = "SELECT state_version, updated_at FROM app_data_state WHERE state_key = %s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, ("dashboard",))
                row = cursor.fetchone()
                if row:
                    return f"{row[0]}|{row[1]}"
        fallback = self.get_max_updated_at() or "none"
        return f"fallback|{fallback}"

    def bump_dashboard_state(self) -> None:
        sql = """
            INSERT INTO app_data_state (state_key, state_version)
            VALUES ('dashboard', 1)
            ON DUPLICATE KEY UPDATE
                state_version = state_version + 1,
                updated_at = CURRENT_TIMESTAMP
        """
        self._client.execute(sql)

class InsiderTradeMySqlRepository(InsiderTradeRepository):
    def fetch_all_symbols(self) -> list[str]:
        sql = "SELECT DISTINCT symbol_at_trade FROM insider_trades WHERE symbol_at_trade IS NOT NULL"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                return [row[0] for row in rows]
