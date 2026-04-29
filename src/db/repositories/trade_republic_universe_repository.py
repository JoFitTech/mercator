from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from src.domain.trade_republic_universe import TradeRepublicUniverseInstrument


class TradeRepublicUniverseRepository:
    def __init__(self, mysql_client) -> None:
        self.mysql_client = mysql_client

    def _connection(self):
        try:
            return self.mysql_client.connection(include_database=True)
        except TypeError:
            return self.mysql_client.connection()

    def get_meta(self, source_url: str | None = None) -> dict[str, Any]:
        if self.mysql_client is None:
            return {}
        with self._connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                if source_url:
                    cur.execute(
                        "SELECT * FROM trade_republic_universe_meta WHERE source_url = %s LIMIT 1",
                        (source_url,),
                    )
                else:
                    cur.execute(
                        "SELECT * FROM trade_republic_universe_meta ORDER BY source_last_refreshed_at DESC LIMIT 1"
                    )
                return cur.fetchone() or {}

    @staticmethod
    def _safe_meta_value(meta: dict[str, Any], key: str, fallback: Any = None) -> Any:
        value = meta.get(key, fallback)
        return fallback if value is None else value

    def is_stale(self, source_url: str, ttl_hours: int) -> bool:
        meta = self.get_meta(source_url)
        refreshed_at = meta.get("source_last_refreshed_at")
        if not isinstance(refreshed_at, datetime):
            return True
        now = datetime.now(UTC)
        ref_utc = refreshed_at.replace(tzinfo=UTC)
        return (now - ref_utc) >= timedelta(hours=max(1, int(ttl_hours)))

    def replace_snapshot(self, instruments: list[TradeRepublicUniverseInstrument], meta: dict[str, Any]) -> None:
        if self.mysql_client is None:
            return
        if not instruments:
            raise ValueError("Snapshot darf nicht leer sein.")

        refreshed_at = meta.get("source_last_refreshed_at") or datetime.now(UTC).replace(tzinfo=None)
        source_url = str(meta.get("source_url") or "")
        source_type = str(meta.get("source_type") or "local_csv")
        source_hash = str(meta.get("source_hash") or "")
        valid_rows = int(meta.get("valid_rows") or len(instruments))
        invalid_rows = int(meta.get("invalid_rows") or 0)
        last_import_status = str(meta.get("last_import_status") or "SUCCESS")

        rows = [
            (
                item.isin,
                item.symbol,
                item.instrument_name,
                item.country,
                item.asset_class,
                source_url,
                refreshed_at,
                source_hash,
            )
            for item in instruments
        ]

        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM trade_republic_universe_reference")
                cur.executemany(
                    """
                    INSERT INTO trade_republic_universe_reference
                    (isin, symbol, instrument_name, country, asset_class, source_url, source_last_refreshed_at, source_hash)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    rows,
                )
                cur.execute(
                    """
                    INSERT INTO trade_republic_universe_meta
                    (source_url, source_last_refreshed_at, source_hash, instrument_count, last_error)
                    VALUES (%s,%s,%s,%s,NULL)
                    ON DUPLICATE KEY UPDATE
                        source_last_refreshed_at = VALUES(source_last_refreshed_at),
                        source_hash = VALUES(source_hash),
                        instrument_count = VALUES(instrument_count),
                        last_error = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (source_url, refreshed_at, source_hash, valid_rows),
                )
                # Optional metrics columns (backward-compatible when absent)
                try:
                    cur.execute(
                        """
                        UPDATE trade_republic_universe_meta
                        SET valid_rows = %s, invalid_rows = %s, source_type = %s, last_import_status = %s
                        WHERE source_url = %s
                        """,
                        (valid_rows, invalid_rows, source_type, last_import_status, source_url),
                    )
                except Exception:
                    pass
            conn.commit()

    def store_error(self, source_url: str, error_text: str) -> None:
        if self.mysql_client is None:
            return
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trade_republic_universe_meta
                    (source_url, source_last_refreshed_at, source_hash, instrument_count, last_error)
                    VALUES (%s, NULL, NULL, 0, %s)
                    ON DUPLICATE KEY UPDATE
                        last_error = VALUES(last_error),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (source_url, str(error_text or "")[:1000]),
                )
                try:
                    cur.execute(
                        """
                        UPDATE trade_republic_universe_meta
                        SET source_type = %s, last_import_status = %s
                        WHERE source_url = %s
                        """,
                        ("local_csv", "FAILED", source_url),
                    )
                except Exception:
                    pass
            conn.commit()

    def find_by_isin(self, isin: str) -> dict[str, Any] | None:
        if self.mysql_client is None:
            return None
        with self._connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    "SELECT isin, symbol, instrument_name FROM trade_republic_universe_reference WHERE isin = %s LIMIT 1",
                    (isin,),
                )
                return cur.fetchone() or None

    def find_by_symbol(self, symbol: str) -> list[dict[str, Any]]:
        if self.mysql_client is None:
            return []
        with self._connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    "SELECT isin, symbol, instrument_name FROM trade_republic_universe_reference WHERE symbol = %s",
                    (symbol,),
                )
                return cur.fetchall() or []

    def search(
        self,
        query: str | None,
        asset_class: str | None,
        country: str | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        if self.mysql_client is None:
            return []
        where = ["1=1"]
        params: list[Any] = []
        text = str(query or "").strip()
        if text:
            like = f"%{text}%"
            where.append("(isin LIKE %s OR symbol LIKE %s OR instrument_name LIKE %s)")
            params.extend([like, like, like])
        if asset_class:
            where.append("asset_class = %s")
            params.append(asset_class)
        if country:
            where.append("country = %s")
            params.append(country)

        sql = (
            "SELECT isin, symbol, instrument_name, country, asset_class, source_url, source_last_refreshed_at "
            "FROM trade_republic_universe_reference "
            f"WHERE {' AND '.join(where)} "
            "ORDER BY instrument_name ASC LIMIT %s OFFSET %s"
        )
        params.extend([int(limit), int(offset)])

        with self._connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(sql, tuple(params))
                return cur.fetchall() or []

    def count(self, query: str | None = None, asset_class: str | None = None, country: str | None = None) -> int:
        if self.mysql_client is None:
            return 0
        where = ["1=1"]
        params: list[Any] = []
        text = str(query or "").strip()
        if text:
            like = f"%{text}%"
            where.append("(isin LIKE %s OR symbol LIKE %s OR instrument_name LIKE %s)")
            params.extend([like, like, like])
        if asset_class:
            where.append("asset_class = %s")
            params.append(asset_class)
        if country:
            where.append("country = %s")
            params.append(country)

        sql = f"SELECT COUNT(*) AS cnt FROM trade_republic_universe_reference WHERE {' AND '.join(where)}"
        with self._connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(sql, tuple(params))
                return int((cur.fetchone() or {}).get("cnt", 0) or 0)

    def count_by_asset_class(self) -> dict[str, int]:
        if self.mysql_client is None:
            return {}
        with self._connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    "SELECT COALESCE(asset_class, 'UNKNOWN') AS key_name, COUNT(*) AS cnt "
                    "FROM trade_republic_universe_reference GROUP BY COALESCE(asset_class, 'UNKNOWN')"
                )
                return {str(r["key_name"]): int(r["cnt"]) for r in (cur.fetchall() or [])}

    def count_by_country(self) -> dict[str, int]:
        if self.mysql_client is None:
            return {}
        with self._connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    "SELECT COALESCE(country, 'UNKNOWN') AS key_name, COUNT(*) AS cnt "
                    "FROM trade_republic_universe_reference GROUP BY COALESCE(country, 'UNKNOWN')"
                )
                return {str(r["key_name"]): int(r["cnt"]) for r in (cur.fetchall() or [])}

