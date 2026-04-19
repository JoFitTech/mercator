"""Repository für API-Nutzungsdaten in MySQL."""

from __future__ import annotations
import datetime
from typing import Any
from mysql.connector import Error, errorcode
from src.db.mysql_client import MySqlClient

class ApiUsageRepository:
    """Persistiert tägliche API-Nutzungskontingente pro Provider."""

    _PRIMARY_TABLE = "app_api_usage"
    _LEGACY_TABLE = "api_usage"

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @classmethod
    def _table_candidates(cls) -> tuple[str, ...]:
        # Primärschema zuerst, dann Legacy-Name für rückwärtskompatible Reads/Writes.
        return (cls._PRIMARY_TABLE, cls._LEGACY_TABLE)

    @staticmethod
    def _is_missing_table_error(exc: Exception) -> bool:
        return isinstance(exc, Error) and getattr(exc, "errno", None) == errorcode.ER_NO_SUCH_TABLE

    def get_usage(self, day_key: datetime.date, provider: str) -> dict[str, Any] | None:
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                for table_name in self._table_candidates():
                    try:
                        query = f"SELECT * FROM {table_name} WHERE day_key = %s AND provider = %s LIMIT 1"
                        cursor.execute(query, (day_key, provider))
                        row = cursor.fetchone()
                        if row:
                            description = cursor.description or []
                            columns = [column[0] for column in description]
                            return dict(zip(columns, row, strict=False))
                        return None
                    except Exception as exc:
                        # Wenn die Tabelle im Zielsystem nicht existiert, probieren wir den Legacy-Namen.
                        if table_name == self._PRIMARY_TABLE and self._is_missing_table_error(exc):
                            continue
                        raise
        return None

    def increment_usage(self, day_key: datetime.date, provider: str, limit_count: int = 250) -> None:
        for table_name in self._table_candidates():
            sql = f"""
                INSERT INTO {table_name} (day_key, provider, call_count, limit_count, last_request_at)
                VALUES (%s, %s, 1, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    call_count = call_count + 1,
                    limit_count = VALUES(limit_count),
                    last_request_at = NOW()
            """
            try:
                self._client.execute(sql, (day_key, provider, limit_count))
                return
            except Exception as exc:
                if table_name == self._PRIMARY_TABLE and self._is_missing_table_error(exc):
                    continue
                raise
