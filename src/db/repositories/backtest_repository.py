"""Repository fuer Backtest-Qualitaetsmetriken."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from src.db.mysql_client import MySqlClient
from src.models.prediction import BacktestResult


class BacktestRepository:
    """Persistiert Backtest-Ergebnisse fuer Modelllaeufe."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    @staticmethod
    def _json_payload(value: Any) -> str:
        return json.dumps(value or {}, sort_keys=True, default=str)

    def _build_payload(self, result: BacktestResult | dict[str, Any]) -> dict[str, Any]:
        payload = asdict(result) if isinstance(result, BacktestResult) else dict(result)
        if not payload.get("model_run_id") or not payload.get("horizon_days"):
            raise ValueError("Backtest payload requires model_run_id and horizon_days.")
        return {
            "backtest_id": payload.get("backtest_id"),
            "model_run_id": str(payload["model_run_id"]),
            "horizon_days": int(payload["horizon_days"]),
            "evaluation_start": payload.get("evaluation_start"),
            "evaluation_end": payload.get("evaluation_end"),
            "sample_size": payload.get("sample_size"),
            "accuracy": payload.get("accuracy"),
            "precision_score": payload.get("precision_score"),
            "recall_score": payload.get("recall_score"),
            "mean_absolute_error": payload.get("mean_absolute_error"),
            "calibration_summary_json": self._json_payload(payload.get("calibration_summary_json")),
            "caveats_text": payload.get("caveats_text"),
        }

    def create_result(self, result: BacktestResult | dict[str, Any]) -> int:
        payload = self._build_payload(result)
        sql = """
            INSERT INTO backtest_results (
                model_run_id, horizon_days, evaluation_start, evaluation_end,
                sample_size, accuracy, precision_score, recall_score,
                mean_absolute_error, calibration_summary_json, caveats_text
            ) VALUES (
                %(model_run_id)s, %(horizon_days)s, %(evaluation_start)s, %(evaluation_end)s,
                %(sample_size)s, %(accuracy)s, %(precision_score)s, %(recall_score)s,
                %(mean_absolute_error)s, %(calibration_summary_json)s, %(caveats_text)s
            )
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, payload)
                backtest_id = int(getattr(cursor, "lastrowid", 0) or 0)
            conn.commit()
        return backtest_id

    def get_latest_for_model(self, model_run_id: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM backtest_results WHERE model_run_id = %s ORDER BY created_at DESC, backtest_id DESC LIMIT 1"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (str(model_run_id),))
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._rows_to_dicts(cursor, [row])[0]

    def list_results(self, model_run_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": max(1, min(int(limit), 5000))}
        sql = "SELECT * FROM backtest_results"
        if model_run_id:
            sql += " WHERE model_run_id = %(model_run_id)s"
            params["model_run_id"] = str(model_run_id)
        sql += " ORDER BY created_at DESC, backtest_id DESC LIMIT %(limit)s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return self._rows_to_dicts(cursor, cursor.fetchall() or [])
