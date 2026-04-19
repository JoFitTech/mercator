"""Repository für Insider-Trades in MySQL."""

from __future__ import annotations
from typing import Any
import pandas as pd
from src.db.mysql_client import MySqlClient

class InsiderTradeRepository:
    """Kapselt CRUD-nahe Zugriffe auf die Tabelle ``insider_trades``."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        """Wandelt Cursor-Resultsets in Listen aus Dictionaries um."""
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    def upsert_trade(self, trade: dict[str, Any]) -> None:
        """Speichert oder aktualisiert genau einen Insider-Trade."""
        sql = """
            INSERT INTO insider_trades (
                company_key, symbol_at_trade, filing_date, transaction_date, reporting_cik, company_cik,
                reporting_name, type_of_owner, transaction_type, acquisition_or_disposition,
                direct_or_indirect, form_type, security_name, qty, price,
                trade_value_estimated, validation_status, dashboard_valid, gate_status, gate_reason, score, score_class,
                profile_status, profile_reason, source_url,
                trade_republic_universe_status, trade_republic_match_method, trade_republic_match_confidence,
                trade_republic_source_refreshed_at, trade_republic_reference_isin, trade_republic_reference_name,
                dedupe_key, fetched_at
            ) VALUES (
                %(company_key)s, %(symbol_at_trade)s, %(filing_date)s, %(transaction_date)s, %(reporting_cik)s, %(company_cik)s,
                %(reporting_name)s, %(type_of_owner)s, %(transaction_type)s, %(acquisition_or_disposition)s,
                %(direct_or_indirect)s, %(form_type)s, %(security_name)s, %(qty)s, %(price)s,
                %(trade_value_estimated)s, %(validation_status)s, %(dashboard_valid)s, %(gate_status)s, %(gate_reason)s, %(score)s, %(score_class)s,
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
            "trade_value_estimated", "validation_status", "dashboard_valid", "gate_status", "gate_reason", "score", "score_class",
            "profile_status", "profile_reason", "source_url",
            "trade_republic_universe_status", "trade_republic_match_method", "trade_republic_match_confidence",
            "trade_republic_source_refreshed_at", "trade_republic_reference_isin", "trade_republic_reference_name",
            "dedupe_key", "fetched_at"
        ]
        params = {k: trade.get(k) for k in fields}
        params["score"] = trade.get("score", trade.get("score_value"))

        self._client.execute(sql, params)

    def upsert_trades(self, trades: list[dict[str, Any]]) -> int:
        """Speichert oder aktualisiert mehrere Insider-Trades im Batch."""
        if not trades:
            return 0
        for t in trades:
            self.upsert_trade(t)
        return len(trades)

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
        conditions: list[str] = []
        params: list[Any] = []

        if filters:
            # dedupe_key Filter (für Trade-Detail-Drilldown)
            if filters.get("dedupe_key"):
                conditions.append("dedupe_key = %s")
                params.append(filters["dedupe_key"])
            if filters.get("date_from"):
                conditions.append("transaction_date >= %s")
                params.append(filters["date_from"])
            if filters.get("date_to"):
                conditions.append("transaction_date <= %s")
                params.append(filters["date_to"])
            # P0.2: UI-Symbolfilter läuft auf symbol_at_trade (Tickerfeld), nicht auf company_key
            if filters.get("symbol"):
                conditions.append("symbol_at_trade LIKE %s")
                params.append(f"%{filters['symbol']}%")
            # Interner company_key-Filter (nicht über UI, nur programmatisch)
            if filters.get("company_key"):
                conditions.append("company_key = %s")
                params.append(filters["company_key"])
            if filters.get("reporting_name"):
                conditions.append("reporting_name LIKE %s")
                params.append(f"%{filters['reporting_name']}%")
            if filters.get("gate_status"):
                conditions.append("gate_status = %s")
                params.append(filters["gate_status"])
            if filters.get("validation_status"):
                conditions.append("validation_status = %s")
                params.append(filters["validation_status"])
            if filters.get("acquisition_or_disposition"):
                conditions.append("acquisition_or_disposition = %s")
                params.append(filters["acquisition_or_disposition"])
            min_score = filters.get("min_score")
            if min_score is not None and min_score > 0:
                conditions.append("score >= %s")
                params.append(min_score)
            if filters.get("trade_republic_universe_status"):
                conditions.append("trade_republic_universe_status = %s")
                params.append(filters["trade_republic_universe_status"])
            if filters.get("dashboard_valid") is not None:
                conditions.append("dashboard_valid = %s")
                params.append(1 if filters["dashboard_valid"] else 0)

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
                c.sector,
                c.industry,
                c.market_cap
            FROM insider_trades t
            LEFT JOIN companies c ON t.company_key = c.company_key
        """
        conditions: list[str] = []
        params: list[Any] = []

        if filters:
            if filters.get("date_from"):
                conditions.append("t.transaction_date >= %s")
                params.append(filters["date_from"])
            if filters.get("date_to"):
                conditions.append("t.transaction_date <= %s")
                params.append(filters["date_to"])
            if filters.get("symbol"):
                conditions.append("t.symbol_at_trade LIKE %s")
                params.append(f"%{filters['symbol']}%")
            if filters.get("company_key"):
                conditions.append("t.company_key = %s")
                params.append(filters["company_key"])
            if filters.get("reporting_name"):
                conditions.append("t.reporting_name LIKE %s")
                params.append(f"%{filters['reporting_name']}%")
            if filters.get("gate_status"):
                conditions.append("t.gate_status = %s")
                params.append(filters["gate_status"])
            if filters.get("validation_status"):
                conditions.append("t.validation_status = %s")
                params.append(filters["validation_status"])
            if filters.get("acquisition_or_disposition"):
                conditions.append("t.acquisition_or_disposition = %s")
                params.append(filters["acquisition_or_disposition"])
            min_score = filters.get("min_score")
            if min_score is not None and min_score > 0:
                conditions.append("t.score >= %s")
                params.append(min_score)
            if filters.get("trade_republic_universe_status"):
                conditions.append("t.trade_republic_universe_status = %s")
                params.append(filters["trade_republic_universe_status"])
            if filters.get("dashboard_valid") is not None:
                conditions.append("t.dashboard_valid = %s")
                params.append(1 if filters["dashboard_valid"] else 0)

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

class InsiderTradeMySqlRepository(InsiderTradeRepository):
    def fetch_all_symbols(self) -> list[str]:
        sql = "SELECT DISTINCT symbol_at_trade FROM insider_trades WHERE symbol_at_trade IS NOT NULL"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                return [row[0] for row in rows]
