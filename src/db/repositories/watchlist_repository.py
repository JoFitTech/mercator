"""Repository fuer die manuelle Watchlist in MySQL."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.db.mysql_client import MySqlClient
from src.models.watchlist import WatchlistItem


class WatchlistRepository:
    """Persistiert Watchlist-Eintraege per Symbol."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    @staticmethod
    def _normalize_symbol(value: Any) -> str:
        return str(value or "").strip().upper()

    @staticmethod
    def _normalize_text(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _normalize_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_bool(value: Any, default: bool = True) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
        return default

    def _build_payload(self, item: WatchlistItem | dict[str, Any]) -> dict[str, Any]:
        payload = asdict(item) if isinstance(item, WatchlistItem) else dict(item)
        symbol = self._normalize_symbol(payload.get("symbol"))
        if not symbol:
            raise ValueError("Watchlist item requires a non-empty symbol.")

        return {
            "symbol": symbol,
            "company_key": self._normalize_text(payload.get("company_key")),
            "display_name": self._normalize_text(payload.get("display_name")),
            "notes": self._normalize_text(payload.get("notes")),
            "priority": self._normalize_int(payload.get("priority"), default=0),
            "active": self._normalize_bool(payload.get("active"), default=True),
            "resolution_status": self._normalize_symbol(payload.get("resolution_status")) or "UNRESOLVED",
        }

    def upsert_item(self, item: WatchlistItem | dict[str, Any]) -> None:
        """Legt einen Watchlist-Eintrag an oder aktualisiert ihn per Symbol."""

        payload = self._build_payload(item)
        sql = """
            INSERT INTO watchlist_items (
                symbol, company_key, display_name, notes, priority, active, resolution_status
            ) VALUES (
                %(symbol)s, %(company_key)s, %(display_name)s, %(notes)s, %(priority)s, %(active)s, %(resolution_status)s
            )
            ON DUPLICATE KEY UPDATE
                company_key = VALUES(company_key),
                display_name = VALUES(display_name),
                notes = VALUES(notes),
                priority = VALUES(priority),
                active = VALUES(active),
                resolution_status = VALUES(resolution_status),
                updated_at = CURRENT_TIMESTAMP
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, payload)
            conn.commit()

    def get_item(self, symbol: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM watchlist_items WHERE symbol = %s LIMIT 1"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (self._normalize_symbol(symbol),))
                row = cursor.fetchone()
                if row is None:
                    return None
                columns = [description[0] for description in cursor.description] if cursor.description else []
                return dict(zip(columns, row, strict=False))

    def list_items(self, active_only: bool = True) -> list[dict[str, Any]]:
        sql = "SELECT * FROM watchlist_items"
        params: tuple[Any, ...] = ()
        if active_only:
            sql += " WHERE active = 1"
        sql += " ORDER BY active DESC, priority DESC, symbol ASC"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall() or []
                return self._rows_to_dicts(cursor, rows)

    def list_unresolved_items(self, active_only: bool = True) -> list[dict[str, Any]]:
        sql = "SELECT * FROM watchlist_items WHERE UPPER(COALESCE(resolution_status, 'UNRESOLVED')) <> 'RESOLVED'"
        params: tuple[Any, ...] = ()
        if active_only:
            sql += " AND active = 1"
        sql += " ORDER BY active DESC, priority DESC, symbol ASC"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall() or []
                return self._rows_to_dicts(cursor, rows)

    def delete_item(self, symbol: str) -> None:
        sql = "DELETE FROM watchlist_items WHERE symbol = %s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (self._normalize_symbol(symbol),))
            conn.commit()

