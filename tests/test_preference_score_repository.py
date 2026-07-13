from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.db.repositories.preference_score_repository import PreferenceScoreRepository
from src.models.preference import PreferenceScore


def _build_mysql_mock() -> tuple[MagicMock, MagicMock, MagicMock]:
    client = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    client.get_connection.return_value.__enter__.return_value = conn
    client.get_connection.return_value.__exit__.return_value = False
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.cursor.return_value.__exit__.return_value = False
    return client, conn, cursor


def test_preference_score_repository_upserts_and_reads_rankings() -> None:
    client, conn, cursor = _build_mysql_mock()
    cursor.lastrowid = 7
    repo = PreferenceScoreRepository(client)

    score_id = repo.upsert_score(
        PreferenceScore(
            symbol="aapl",
            score_as_of=date(2026, 7, 10),
            preference_score=82.5,
            rank_position=1,
            fundamental_component=80,
            technical_component=75,
            risk_component=70,
            prediction_component=90,
            confidence_component=85,
            confidence=0.74,
            uncertainty=0.12,
            explanation_positive="Preference supported by solid fundamentals.",
            explanation_negative="No major deprioritizing component is visible.",
            data_quality_summary="All required scoring inputs are available.",
        )
    )

    assert score_id == 7
    sql, params = cursor.execute.call_args[0]
    assert "INSERT INTO preference_scores" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert params["symbol"] == "AAPL"
    assert params["rank_position"] == 1
    assert params["data_quality_summary"] == "All required scoring inputs are available."
    conn.commit.assert_called()

    cursor.description = [("symbol",), ("rank_position",), ("preference_score",)]
    cursor.fetchall.return_value = [("AAPL", 1, 82.5), ("MSFT", 2, 76.0)]
    rows = repo.list_rankings(score_as_of=date(2026, 7, 10))
    assert rows == [
        {"symbol": "AAPL", "rank_position": 1, "preference_score": 82.5},
        {"symbol": "MSFT", "rank_position": 2, "preference_score": 76.0},
    ]

    cursor.fetchone.return_value = ("AAPL", 1, 82.5)
    assert repo.get_latest("aapl") == {"symbol": "AAPL", "rank_position": 1, "preference_score": 82.5}


def test_preference_score_repository_requires_symbol_and_date() -> None:
    repo = PreferenceScoreRepository(_build_mysql_mock()[0])
    with pytest.raises(ValueError):
        repo.upsert_score({"symbol": "", "score_as_of": date(2026, 7, 10)})
    with pytest.raises(ValueError):
        repo.upsert_score({"symbol": "AAPL"})
