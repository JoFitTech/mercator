"""Repository fuer normalisierte historische Tagespreise."""

from __future__ import annotations

from typing import Any

from src.db.mysql_client import MySqlClient


class StockPriceRepository:
    """Persistiert clean price history fuer Watchlist-Symbole."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    @staticmethod
    def _build_payload(row: dict[str, Any]) -> dict[str, Any]:
        symbol = str(row.get("symbol") or "").strip().upper()
        provider = str(row.get("provider") or "FMP").strip().upper()
        if not symbol or not row.get("price_date"):
            raise ValueError("Stock price rows require symbol and price_date.")
        return {
            "symbol": symbol,
            "price_date": row["price_date"],
            "open_price": row.get("open_price"),
            "high_price": row.get("high_price"),
            "low_price": row.get("low_price"),
            "close_price": row.get("close_price"),
            "adjusted_close": row.get("adjusted_close"),
            "volume": row.get("volume"),
            "provider": provider,
            "source_refreshed_at": row.get("source_refreshed_at"),
            "quality_status": str(row.get("quality_status") or "UNKNOWN").strip().upper(),
        }

    def upsert_prices(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        payloads = [self._build_payload(row) for row in rows]
        sql = """
            INSERT INTO stock_price_history (
                symbol, price_date, open_price, high_price, low_price, close_price,
                adjusted_close, volume, provider, source_refreshed_at, quality_status
            ) VALUES (
                %(symbol)s, %(price_date)s, %(open_price)s, %(high_price)s, %(low_price)s, %(close_price)s,
                %(adjusted_close)s, %(volume)s, %(provider)s, %(source_refreshed_at)s, %(quality_status)s
            )
            ON DUPLICATE KEY UPDATE
                open_price = VALUES(open_price),
                high_price = VALUES(high_price),
                low_price = VALUES(low_price),
                close_price = VALUES(close_price),
                adjusted_close = VALUES(adjusted_close),
                volume = VALUES(volume),
                source_refreshed_at = VALUES(source_refreshed_at),
                quality_status = VALUES(quality_status),
                updated_at = CURRENT_TIMESTAMP
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, payloads)
            conn.commit()
        return len(payloads)

    def list_prices(self, symbol: str, provider: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"symbol": str(symbol).strip().upper(), "limit": max(1, min(int(limit), 5000))}
        sql = "SELECT * FROM stock_price_history WHERE symbol = %(symbol)s"
        if provider:
            sql += " AND provider = %(provider)s"
            params["provider"] = str(provider).strip().upper()
        sql += " ORDER BY price_date DESC LIMIT %(limit)s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return self._rows_to_dicts(cursor, cursor.fetchall() or [])

    def get_latest_price_date(self, symbol: str, provider: str | None = None) -> Any | None:
        params: dict[str, Any] = {"symbol": str(symbol).strip().upper()}
        sql = "SELECT MAX(price_date) FROM stock_price_history WHERE symbol = %(symbol)s"
        if provider:
            sql += " AND provider = %(provider)s"
            params["provider"] = str(provider).strip().upper()
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
                return row[0] if row else None
