"""Repository fuer persistente API3-Signale."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.db.mysql_client import MySqlClient


class MarketSignalCacheRepository:
    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    def get_symbol_cache(self, symbol: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM market_signal_cache WHERE symbol = %s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (symbol,))
                row = cursor.fetchone()
                if not row:
                    return None
                columns = [d[0] for d in cursor.description] if cursor.description else []
                return dict(zip(columns, row, strict=False))

    def upsert_symbol_cache(self, payload: dict[str, Any]) -> None:
        sql = """
            INSERT INTO market_signal_cache (
                symbol, from_date, to_date,
                avg_20d_volume, avg_20d_dollar_volume, sma_50, sma_200,
                momentum_3m, momentum_6m, technical_state, liquidity_state,
                refreshed_at
            ) VALUES (
                %(symbol)s, %(from_date)s, %(to_date)s,
                %(avg_20d_volume)s, %(avg_20d_dollar_volume)s, %(sma_50)s, %(sma_200)s,
                %(momentum_3m)s, %(momentum_6m)s, %(technical_state)s, %(liquidity_state)s,
                %(refreshed_at)s
            )
            ON DUPLICATE KEY UPDATE
                from_date = VALUES(from_date),
                to_date = VALUES(to_date),
                avg_20d_volume = VALUES(avg_20d_volume),
                avg_20d_dollar_volume = VALUES(avg_20d_dollar_volume),
                sma_50 = VALUES(sma_50),
                sma_200 = VALUES(sma_200),
                momentum_3m = VALUES(momentum_3m),
                momentum_6m = VALUES(momentum_6m),
                technical_state = VALUES(technical_state),
                liquidity_state = VALUES(liquidity_state),
                refreshed_at = VALUES(refreshed_at)
        """
        self._client.execute(sql, payload)

    @staticmethod
    def parse_date(value: Any) -> date | None:
        if isinstance(value, date):
            return value
        return None
