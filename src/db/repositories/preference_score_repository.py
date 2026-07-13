"""Repository fuer transparente Preference Scores."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.db.mysql_client import MySqlClient
from src.models.preference import PreferenceScore


class PreferenceScoreRepository:
    """Persistiert und liest Watchlist-Rankings aus `preference_scores`."""

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
    def _build_payload(score: PreferenceScore | dict[str, Any]) -> dict[str, Any]:
        payload = asdict(score) if isinstance(score, PreferenceScore) else dict(score)
        symbol = PreferenceScoreRepository._normalize_symbol(payload.get("symbol"))
        if not symbol or not payload.get("score_as_of"):
            raise ValueError("Preference score payload requires symbol and score_as_of.")
        return {
            "preference_score_id": payload.get("preference_score_id"),
            "symbol": symbol,
            "score_as_of": payload["score_as_of"],
            "preference_score": payload.get("preference_score"),
            "rank_position": payload.get("rank_position"),
            "fundamental_component": payload.get("fundamental_component"),
            "technical_component": payload.get("technical_component"),
            "risk_component": payload.get("risk_component"),
            "prediction_component": payload.get("prediction_component"),
            "confidence_component": payload.get("confidence_component"),
            "confidence": payload.get("confidence"),
            "uncertainty": payload.get("uncertainty"),
            "explanation_positive": payload.get("explanation_positive"),
            "explanation_negative": payload.get("explanation_negative"),
            "data_quality_summary": payload.get("data_quality_summary"),
        }

    def upsert_score(self, score: PreferenceScore | dict[str, Any]) -> int | None:
        payload = self._build_payload(score)
        sql = """
            INSERT INTO preference_scores (
                symbol, score_as_of, preference_score, rank_position,
                fundamental_component, technical_component, risk_component,
                prediction_component, confidence_component, confidence, uncertainty,
                explanation_positive, explanation_negative, data_quality_summary
            ) VALUES (
                %(symbol)s, %(score_as_of)s, %(preference_score)s, %(rank_position)s,
                %(fundamental_component)s, %(technical_component)s, %(risk_component)s,
                %(prediction_component)s, %(confidence_component)s, %(confidence)s, %(uncertainty)s,
                %(explanation_positive)s, %(explanation_negative)s, %(data_quality_summary)s
            )
            ON DUPLICATE KEY UPDATE
                preference_score = VALUES(preference_score),
                rank_position = VALUES(rank_position),
                fundamental_component = VALUES(fundamental_component),
                technical_component = VALUES(technical_component),
                risk_component = VALUES(risk_component),
                prediction_component = VALUES(prediction_component),
                confidence_component = VALUES(confidence_component),
                confidence = VALUES(confidence),
                uncertainty = VALUES(uncertainty),
                explanation_positive = VALUES(explanation_positive),
                explanation_negative = VALUES(explanation_negative),
                data_quality_summary = VALUES(data_quality_summary)
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, payload)
                score_id = getattr(cursor, "lastrowid", None)
            conn.commit()
        return int(score_id) if score_id else payload.get("preference_score_id")

    def upsert_scores(self, scores: list[PreferenceScore | dict[str, Any]]) -> int:
        for score in scores:
            self.upsert_score(score)
        return len(scores)

    def get_latest(self, symbol: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM preference_scores WHERE symbol = %s ORDER BY score_as_of DESC, created_at DESC LIMIT 1"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (self._normalize_symbol(symbol),))
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._rows_to_dicts(cursor, [row])[0]

    def list_rankings(self, score_as_of: Any | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": max(1, min(int(limit), 5000))}
        sql = "SELECT * FROM preference_scores"
        if score_as_of is not None:
            sql += " WHERE score_as_of = %(score_as_of)s"
            params["score_as_of"] = score_as_of
        sql += " ORDER BY score_as_of DESC, rank_position ASC, preference_score DESC LIMIT %(limit)s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return self._rows_to_dicts(cursor, cursor.fetchall() or [])
