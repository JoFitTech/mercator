"""Repositories fuer Prediction-Modelllaeufe und Ergebnisdaten."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from src.db.mysql_client import MySqlClient
from src.models.prediction import ModelRun, PredictionResult


class PredictionRepository:
    """Persistiert Modelllaeufe und Symbol-Prognosen."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    @staticmethod
    def _normalize_text(value: Any, default: str) -> str:
        text = str(value or "").strip()
        return text or default

    @staticmethod
    def _normalize_upper(value: Any, default: str) -> str:
        return PredictionRepository._normalize_text(value, default).upper()

    @staticmethod
    def _json_payload(value: Any) -> str:
        return json.dumps(value or {}, sort_keys=True, default=str)

    def _build_model_run_payload(self, run: ModelRun | dict[str, Any]) -> dict[str, Any]:
        payload = asdict(run) if isinstance(run, ModelRun) else dict(run)
        required = ("model_run_id", "model_name", "model_type", "model_version", "target_type", "horizon_days")
        missing = [field for field in required if not payload.get(field)]
        if missing:
            raise ValueError(f"Model run payload requires: {', '.join(missing)}")
        return {
            "model_run_id": str(payload["model_run_id"]),
            "model_name": self._normalize_text(payload.get("model_name"), "unknown_model"),
            "model_type": self._normalize_upper(payload.get("model_type"), "BASELINE"),
            "model_version": self._normalize_text(payload.get("model_version"), "v1"),
            "target_type": self._normalize_text(payload.get("target_type"), "expected_return"),
            "horizon_days": int(payload["horizon_days"]),
            "training_started_at": payload.get("training_started_at"),
            "training_completed_at": payload.get("training_completed_at"),
            "training_window_start": payload.get("training_window_start"),
            "training_window_end": payload.get("training_window_end"),
            "feature_set_version": payload.get("feature_set_version"),
            "status": self._normalize_upper(payload.get("status"), "PENDING"),
            "quality_summary_json": self._json_payload(payload.get("quality_summary_json")),
            "error_message": payload.get("error_message"),
        }

    def _build_prediction_payload(self, prediction: PredictionResult | dict[str, Any]) -> dict[str, Any]:
        payload = asdict(prediction) if isinstance(prediction, PredictionResult) else dict(prediction)
        required = ("model_run_id", "symbol", "prediction_as_of", "horizon_days", "target_type")
        missing = [field for field in required if not payload.get(field)]
        if missing:
            raise ValueError(f"Prediction payload requires: {', '.join(missing)}")
        return {
            "prediction_id": payload.get("prediction_id"),
            "model_run_id": str(payload["model_run_id"]),
            "symbol": str(payload["symbol"]).strip().upper(),
            "prediction_as_of": payload["prediction_as_of"],
            "horizon_days": int(payload["horizon_days"]),
            "target_type": self._normalize_text(payload.get("target_type"), "expected_return"),
            "direction": self._normalize_upper(payload.get("direction"), "") or None,
            "return_class": self._normalize_upper(payload.get("return_class"), "") or None,
            "expected_return": payload.get("expected_return"),
            "confidence": payload.get("confidence"),
            "uncertainty": payload.get("uncertainty"),
            "model_quality_score": payload.get("model_quality_score"),
            "input_refreshed_at": payload.get("input_refreshed_at"),
        }

    def upsert_model_run(self, run: ModelRun | dict[str, Any]) -> str:
        payload = self._build_model_run_payload(run)
        sql = """
            INSERT INTO model_runs (
                model_run_id, model_name, model_type, model_version, target_type, horizon_days,
                training_started_at, training_completed_at, training_window_start, training_window_end,
                feature_set_version, status, quality_summary_json, error_message
            ) VALUES (
                %(model_run_id)s, %(model_name)s, %(model_type)s, %(model_version)s, %(target_type)s, %(horizon_days)s,
                %(training_started_at)s, %(training_completed_at)s, %(training_window_start)s, %(training_window_end)s,
                %(feature_set_version)s, %(status)s, %(quality_summary_json)s, %(error_message)s
            )
            ON DUPLICATE KEY UPDATE
                model_name = VALUES(model_name),
                model_type = VALUES(model_type),
                model_version = VALUES(model_version),
                target_type = VALUES(target_type),
                horizon_days = VALUES(horizon_days),
                training_started_at = VALUES(training_started_at),
                training_completed_at = VALUES(training_completed_at),
                training_window_start = VALUES(training_window_start),
                training_window_end = VALUES(training_window_end),
                feature_set_version = VALUES(feature_set_version),
                status = VALUES(status),
                quality_summary_json = VALUES(quality_summary_json),
                error_message = VALUES(error_message),
                updated_at = CURRENT_TIMESTAMP
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, payload)
            conn.commit()
        return payload["model_run_id"]

    def get_model_run(self, model_run_id: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM model_runs WHERE model_run_id = %s LIMIT 1"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (str(model_run_id),))
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._rows_to_dicts(cursor, [row])[0]

    def list_model_runs(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": max(1, min(int(limit), 5000))}
        sql = "SELECT * FROM model_runs"
        if status:
            sql += " WHERE UPPER(status) = %(status)s"
            params["status"] = self._normalize_upper(status, "READY")
        sql += " ORDER BY training_completed_at DESC, created_at DESC LIMIT %(limit)s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return self._rows_to_dicts(cursor, cursor.fetchall() or [])

    def mark_obsolete_versions(
        self,
        model_name: str,
        horizon_days: int,
        target_type: str,
        keep_model_run_id: str,
    ) -> int:
        sql = """
            UPDATE model_runs
            SET status = 'OBSOLETE',
                updated_at = CURRENT_TIMESTAMP
            WHERE model_name = %(model_name)s
              AND horizon_days = %(horizon_days)s
              AND target_type = %(target_type)s
              AND model_run_id <> %(keep_model_run_id)s
              AND UPPER(status) = 'READY'
        """
        params = {
            "model_name": self._normalize_text(model_name, "unknown_model"),
            "horizon_days": int(horizon_days),
            "target_type": self._normalize_text(target_type, "expected_return"),
            "keep_model_run_id": str(keep_model_run_id),
        }
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                affected = int(getattr(cursor, "rowcount", 0) or 0)
            conn.commit()
        return affected

    def upsert_prediction(self, prediction: PredictionResult | dict[str, Any]) -> int | None:
        payload = self._build_prediction_payload(prediction)
        sql = """
            INSERT INTO prediction_results (
                model_run_id, symbol, prediction_as_of, horizon_days, target_type,
                direction, return_class, expected_return, confidence, uncertainty,
                model_quality_score, input_refreshed_at
            ) VALUES (
                %(model_run_id)s, %(symbol)s, %(prediction_as_of)s, %(horizon_days)s, %(target_type)s,
                %(direction)s, %(return_class)s, %(expected_return)s, %(confidence)s, %(uncertainty)s,
                %(model_quality_score)s, %(input_refreshed_at)s
            )
            ON DUPLICATE KEY UPDATE
                direction = VALUES(direction),
                return_class = VALUES(return_class),
                expected_return = VALUES(expected_return),
                confidence = VALUES(confidence),
                uncertainty = VALUES(uncertainty),
                model_quality_score = VALUES(model_quality_score),
                input_refreshed_at = VALUES(input_refreshed_at)
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, payload)
                prediction_id = getattr(cursor, "lastrowid", None)
            conn.commit()
        return int(prediction_id) if prediction_id else payload.get("prediction_id")

    def upsert_predictions(self, predictions: list[PredictionResult | dict[str, Any]]) -> int:
        for prediction in predictions:
            self.upsert_prediction(prediction)
        return len(predictions)

    def list_predictions(
        self,
        model_run_id: str | None = None,
        symbol: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {"limit": max(1, min(int(limit), 5000))}
        if model_run_id:
            clauses.append("model_run_id = %(model_run_id)s")
            params["model_run_id"] = str(model_run_id)
        if symbol:
            clauses.append("symbol = %(symbol)s")
            params["symbol"] = str(symbol).strip().upper()
        sql = "SELECT * FROM prediction_results"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY prediction_as_of DESC, created_at DESC LIMIT %(limit)s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return self._rows_to_dicts(cursor, cursor.fetchall() or [])
