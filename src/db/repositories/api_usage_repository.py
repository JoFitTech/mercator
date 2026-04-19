"""Repository für API-Nutzungsdaten in MySQL."""

from __future__ import annotations
import datetime
from typing import Any
from src.db.mysql_client import MySqlClient

class ApiUsageRepository:
    """Persistiert tägliche API-Nutzungskontingente pro Provider."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    def get_usage(self, day_key: datetime.date, provider: str) -> dict[str, Any] | None:
        query = "SELECT * FROM api_usage WHERE day_key = %s AND provider = %s LIMIT 1"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (day_key, provider))
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row, strict=False))
        return None

    def increment_usage(self, day_key: datetime.date, provider: str, limit_count: int = 250) -> None:
        sql = """
            INSERT INTO api_usage (day_key, provider, call_count, limit_count, last_request_at)
            VALUES (%s, %s, 1, %s, NOW())
            ON DUPLICATE KEY UPDATE
                call_count = call_count + 1,
                limit_count = VALUES(limit_count),
                last_request_at = NOW()
        """
        self._client.execute(sql, (day_key, provider, limit_count))
