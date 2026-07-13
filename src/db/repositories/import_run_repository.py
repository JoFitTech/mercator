"""Repository fuer Import-Run-Metadaten in MySQL."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.db.mysql_client import MySqlClient
from src.models.stock import ImportRunSummary


class ImportRunRepository:
    """Persistiert Import-Run-Zusammenfassungen."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    @staticmethod
    def _normalize_status(value: Any, default: str = "PENDING") -> str:
        normalized = str(value or "").strip().upper()
        return normalized or default

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _build_payload(self, run: ImportRunSummary | dict[str, Any]) -> dict[str, Any]:
        payload = asdict(run) if isinstance(run, ImportRunSummary) else dict(run)
        required_fields = ("import_run_id", "provider", "import_type", "started_at")
        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            raise ValueError(f"Import run payload requires: {', '.join(missing)}")

        return {
            "import_run_id": str(payload["import_run_id"]),
            "provider": str(payload["provider"]),
            "import_type": str(payload["import_type"]),
            "started_at": payload["started_at"],
            "completed_at": payload.get("completed_at"),
            "status": self._normalize_status(payload.get("status")),
            "symbols_requested": self._coerce_int(payload.get("symbols_requested")),
            "symbols_succeeded": self._coerce_int(payload.get("symbols_succeeded")),
            "symbols_failed": self._coerce_int(payload.get("symbols_failed")),
            "raw_responses_written": self._coerce_int(payload.get("raw_responses_written")),
            "clean_records_written": self._coerce_int(payload.get("clean_records_written")),
            "error_message": payload.get("error_message"),
        }

    def upsert_run(self, run: ImportRunSummary | dict[str, Any]) -> str:
        """Speichert oder aktualisiert einen Import-Run und gibt die stabile ID zurueck."""

        payload = self._build_payload(run)
        sql = """
            INSERT INTO import_runs (
                import_run_id, provider, import_type, started_at, completed_at, status,
                symbols_requested, symbols_succeeded, symbols_failed,
                raw_responses_written, clean_records_written, error_message
            ) VALUES (
                %(import_run_id)s, %(provider)s, %(import_type)s, %(started_at)s, %(completed_at)s, %(status)s,
                %(symbols_requested)s, %(symbols_succeeded)s, %(symbols_failed)s,
                %(raw_responses_written)s, %(clean_records_written)s, %(error_message)s
            )
            ON DUPLICATE KEY UPDATE
                provider = VALUES(provider),
                import_type = VALUES(import_type),
                started_at = VALUES(started_at),
                completed_at = COALESCE(VALUES(completed_at), completed_at),
                status = VALUES(status),
                symbols_requested = VALUES(symbols_requested),
                symbols_succeeded = VALUES(symbols_succeeded),
                symbols_failed = VALUES(symbols_failed),
                raw_responses_written = VALUES(raw_responses_written),
                clean_records_written = VALUES(clean_records_written),
                error_message = VALUES(error_message),
                updated_at = CURRENT_TIMESTAMP
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, payload)
            conn.commit()
        return payload["import_run_id"]

    def get_run(self, import_run_id: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM import_runs WHERE import_run_id = %s LIMIT 1"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (import_run_id,))
                row = cursor.fetchone()
                if row is None:
                    return None
                columns = [description[0] for description in cursor.description] if cursor.description else []
                return dict(zip(columns, row, strict=False))

    def list_runs(
        self,
        provider: str | None = None,
        import_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {
            "limit": max(1, min(int(limit), 5000)),
            "offset": max(0, int(offset)),
        }
        if provider:
            clauses.append("provider = %(provider)s")
            params["provider"] = provider
        if import_type:
            clauses.append("import_type = %(import_type)s")
            params["import_type"] = import_type
        if status:
            clauses.append("UPPER(status) = %(status)s")
            params["status"] = self._normalize_status(status)

        sql = "SELECT * FROM import_runs"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY started_at DESC, import_run_id DESC LIMIT %(limit)s OFFSET %(offset)s"

        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall() or []
                return self._rows_to_dicts(cursor, rows)

    def count_runs(
        self,
        provider: str | None = None,
        import_type: str | None = None,
        status: str | None = None,
    ) -> int:
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if provider:
            clauses.append("provider = %(provider)s")
            params["provider"] = provider
        if import_type:
            clauses.append("import_type = %(import_type)s")
            params["import_type"] = import_type
        if status:
            clauses.append("UPPER(status) = %(status)s")
            params["status"] = self._normalize_status(status)

        sql = "SELECT COUNT(*) AS cnt FROM import_runs"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)

        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
                if not row:
                    return 0
                return int(row[0])
