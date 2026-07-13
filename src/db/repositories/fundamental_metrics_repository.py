"""Repository fuer normalisierte Finanz- und Bewertungsmetriken."""

from __future__ import annotations

from typing import Any

from src.db.mysql_client import MySqlClient


class FundamentalMetricsRepository:
    """Persistiert clean fundamental/valuation metrics fuer Watchlist-Symbole."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    @staticmethod
    def _build_payload(row: dict[str, Any]) -> dict[str, Any]:
        symbol = str(row.get("symbol") or "").strip().upper()
        metric_name = str(row.get("metric_name") or "").strip()
        provider = str(row.get("provider") or "FMP").strip().upper()
        if not symbol or not metric_name or not row.get("period_end"):
            raise ValueError("Fundamental metric rows require symbol, metric_name, and period_end.")
        return {
            "symbol": symbol,
            "metric_name": metric_name,
            "period_type": str(row.get("period_type") or "annual").strip().upper(),
            "period_end": row["period_end"],
            "value": row.get("value"),
            "unit": row.get("unit"),
            "provider": provider,
            "source_refreshed_at": row.get("source_refreshed_at"),
            "quality_status": str(row.get("quality_status") or "UNKNOWN").strip().upper(),
        }

    def upsert_metrics(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        payloads = [self._build_payload(row) for row in rows]
        sql = """
            INSERT INTO fundamental_metrics (
                symbol, metric_name, period_type, period_end, value, unit,
                provider, source_refreshed_at, quality_status
            ) VALUES (
                %(symbol)s, %(metric_name)s, %(period_type)s, %(period_end)s, %(value)s, %(unit)s,
                %(provider)s, %(source_refreshed_at)s, %(quality_status)s
            )
            ON DUPLICATE KEY UPDATE
                value = VALUES(value),
                unit = VALUES(unit),
                source_refreshed_at = VALUES(source_refreshed_at),
                quality_status = VALUES(quality_status),
                updated_at = CURRENT_TIMESTAMP
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, payloads)
            conn.commit()
        return len(payloads)

    def list_metrics(
        self,
        symbol: str,
        metric_name: str | None = None,
        provider: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"symbol": str(symbol).strip().upper(), "limit": max(1, min(int(limit), 5000))}
        sql = "SELECT * FROM fundamental_metrics WHERE symbol = %(symbol)s"
        if metric_name:
            sql += " AND metric_name = %(metric_name)s"
            params["metric_name"] = str(metric_name).strip()
        if provider:
            sql += " AND provider = %(provider)s"
            params["provider"] = str(provider).strip().upper()
        sql += " ORDER BY period_end DESC, metric_name ASC LIMIT %(limit)s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return self._rows_to_dicts(cursor, cursor.fetchall() or [])
