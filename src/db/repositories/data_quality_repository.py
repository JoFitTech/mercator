"""Repository fuer sichtbare Datenqualitaetsprobleme in MySQL."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from src.db.mysql_client import MySqlClient
from src.models.watchlist import DataQualityIssue


class DataQualityRepository:
    """Persistiert und liest Datenqualitaetsissues fuer Stock-Analyse-Daten."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    @staticmethod
    def _normalize_text(value: Any, default: str) -> str:
        normalized = str(value or "").strip().upper()
        return normalized or default

    @staticmethod
    def _normalize_message(value: Any) -> str:
        text = str(value or "").strip()
        return text or "No data-quality message provided."

    @staticmethod
    def _normalize_datetime(value: Any, default: datetime | None = None) -> datetime | None:
        if value is None:
            return default
        return value

    def _build_payload(self, issue: DataQualityIssue | dict[str, Any]) -> dict[str, Any]:
        payload = asdict(issue) if isinstance(issue, DataQualityIssue) else dict(issue)
        required_fields = ("symbol", "data_category", "severity", "message", "detected_at")
        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            raise ValueError(f"Data-quality issue payload requires: {', '.join(missing)}")

        return {
            "issue_id": payload.get("issue_id"),
            "symbol": str(payload["symbol"]).strip().upper(),
            "data_category": str(payload["data_category"]).strip(),
            "severity": self._normalize_text(payload.get("severity"), "WARNING"),
            "status": self._normalize_text(payload.get("status"), "OPEN"),
            "message": self._normalize_message(payload.get("message")),
            "detected_at": payload["detected_at"],
            "source_refreshed_at": self._normalize_datetime(payload.get("source_refreshed_at")),
            "resolved_at": self._normalize_datetime(payload.get("resolved_at")),
        }

    def create_issue(self, issue: DataQualityIssue | dict[str, Any]) -> int:
        """Legt ein neues Issue an und gibt die issue_id zurueck."""

        payload = self._build_payload(issue)
        sql = """
            INSERT INTO data_quality_issues (
                symbol, data_category, severity, status, message,
                detected_at, source_refreshed_at, resolved_at
            ) VALUES (
                %(symbol)s, %(data_category)s, %(severity)s, %(status)s, %(message)s,
                %(detected_at)s, %(source_refreshed_at)s, %(resolved_at)s
            )
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, payload)
                issue_id = int(getattr(cursor, "lastrowid", 0) or 0)
            conn.commit()
        return issue_id

    def update_issue(self, issue: DataQualityIssue | dict[str, Any]) -> int:
        """Aktualisiert ein bestehendes Issue anhand seiner issue_id."""

        payload = self._build_payload(issue)
        issue_id = payload.get("issue_id")
        if issue_id is None:
            return self.create_issue(payload)

        sql = """
            UPDATE data_quality_issues
            SET symbol = %(symbol)s,
                data_category = %(data_category)s,
                severity = %(severity)s,
                status = %(status)s,
                message = %(message)s,
                detected_at = %(detected_at)s,
                source_refreshed_at = %(source_refreshed_at)s,
                resolved_at = %(resolved_at)s,
                updated_at = CURRENT_TIMESTAMP
            WHERE issue_id = %(issue_id)s
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, payload)
            conn.commit()
        return int(issue_id)

    def upsert_issue(self, issue: DataQualityIssue | dict[str, Any]) -> int:
        """Speichert ein Issue neu oder aktualisiert es anhand der issue_id."""

        payload = self._build_payload(issue)
        if payload.get("issue_id") is None:
            return self.create_issue(payload)
        return self.update_issue(payload)

    def get_issue(self, issue_id: int) -> dict[str, Any] | None:
        sql = "SELECT * FROM data_quality_issues WHERE issue_id = %s LIMIT 1"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (issue_id,))
                row = cursor.fetchone()
                if row is None:
                    return None
                columns = [description[0] for description in cursor.description] if cursor.description else []
                return dict(zip(columns, row, strict=False))

    def list_issues(
        self,
        symbol: str | None = None,
        data_category: str | None = None,
        status: str | None = None,
        unresolved_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {
            "limit": max(1, min(int(limit), 5000)),
            "offset": max(0, int(offset)),
        }
        if symbol:
            clauses.append("symbol = %(symbol)s")
            params["symbol"] = str(symbol).strip().upper()
        if data_category:
            clauses.append("data_category = %(data_category)s")
            params["data_category"] = str(data_category).strip()
        if status:
            clauses.append("UPPER(status) = %(status)s")
            params["status"] = self._normalize_text(status, "OPEN")
        elif unresolved_only:
            clauses.append("UPPER(status) <> 'RESOLVED'")

        sql = "SELECT * FROM data_quality_issues"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY detected_at DESC, issue_id DESC LIMIT %(limit)s OFFSET %(offset)s"

        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall() or []
                return self._rows_to_dicts(cursor, rows)

    def count_issues(
        self,
        symbol: str | None = None,
        data_category: str | None = None,
        status: str | None = None,
        unresolved_only: bool = False,
    ) -> int:
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if symbol:
            clauses.append("symbol = %(symbol)s")
            params["symbol"] = str(symbol).strip().upper()
        if data_category:
            clauses.append("data_category = %(data_category)s")
            params["data_category"] = str(data_category).strip()
        if status:
            clauses.append("UPPER(status) = %(status)s")
            params["status"] = self._normalize_text(status, "OPEN")
        elif unresolved_only:
            clauses.append("UPPER(status) <> 'RESOLVED'")

        sql = "SELECT COUNT(*) AS cnt FROM data_quality_issues"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)

        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
                if not row:
                    return 0
                return int(row[0])

    def resolve_issue(self, issue_id: int, resolved_at: datetime | None = None) -> int:
        resolved_at = resolved_at or datetime.now(timezone.utc)
        sql = """
            UPDATE data_quality_issues
            SET status = 'RESOLVED',
                resolved_at = %(resolved_at)s,
                updated_at = CURRENT_TIMESTAMP
            WHERE issue_id = %(issue_id)s
        """
        params = {"issue_id": issue_id, "resolved_at": resolved_at}
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
            conn.commit()
        return issue_id

