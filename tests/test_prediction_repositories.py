from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.db.repositories.backtest_repository import BacktestRepository
from src.db.repositories.prediction_repository import PredictionRepository
from src.models.prediction import BacktestResult, ModelRun, PredictionResult


def _build_mysql_mock() -> tuple[MagicMock, MagicMock, MagicMock]:
    client = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    client.get_connection.return_value.__enter__.return_value = conn
    client.get_connection.return_value.__exit__.return_value = False
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.cursor.return_value.__exit__.return_value = False
    return client, conn, cursor


def test_prediction_repository_upserts_model_runs_and_predictions() -> None:
    client, conn, cursor = _build_mysql_mock()
    repo = PredictionRepository(client)
    run = ModelRun(
        model_run_id="baseline-expected_return-20d-20260710120000",
        model_name="baseline",
        model_type="baseline",
        model_version="v1",
        target_type="expected_return",
        horizon_days=20,
        status="ready",
        quality_summary_json={"quality_score": 0.75},
    )

    assert repo.upsert_model_run(run) == run.model_run_id
    sql, params = cursor.execute.call_args[0]
    assert "INSERT INTO model_runs" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert params["model_type"] == "BASELINE"
    assert params["status"] == "READY"
    assert '"quality_score": 0.75' in params["quality_summary_json"]
    conn.commit.assert_called()

    prediction = PredictionResult(
        model_run_id=run.model_run_id,
        symbol="aapl",
        prediction_as_of=date(2026, 7, 9),
        horizon_days=20,
        target_type="expected_return",
        direction="positive",
        expected_return=0.04,
        confidence=0.7,
        uncertainty=0.15,
        model_quality_score=0.75,
    )
    repo.upsert_prediction(prediction)
    sql, params = cursor.execute.call_args[0]
    assert "INSERT INTO prediction_results" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert params["symbol"] == "AAPL"
    assert params["direction"] == "POSITIVE"

    cursor.description = [("model_run_id",), ("status",)]
    cursor.fetchone.return_value = (run.model_run_id, "READY")
    assert repo.get_model_run(run.model_run_id) == {"model_run_id": run.model_run_id, "status": "READY"}

    cursor.rowcount = 2
    assert repo.mark_obsolete_versions("baseline", 20, "expected_return", run.model_run_id) == 2
    sql, params = cursor.execute.call_args[0]
    assert "SET status = 'OBSOLETE'" in sql
    assert params["keep_model_run_id"] == run.model_run_id


def test_backtest_repository_creates_and_lists_results() -> None:
    client, conn, cursor = _build_mysql_mock()
    cursor.lastrowid = 42
    repo = BacktestRepository(client)
    result = BacktestResult(
        model_run_id="run-1",
        horizon_days=20,
        evaluation_start=date(2026, 1, 1),
        evaluation_end=date(2026, 6, 1),
        sample_size=12,
        accuracy=0.66,
        calibration_summary_json={"avg_actual_return": 0.03},
        caveats_text="Small sample.",
    )

    assert repo.create_result(result) == 42
    sql, params = cursor.execute.call_args[0]
    assert "INSERT INTO backtest_results" in sql
    assert params["model_run_id"] == "run-1"
    assert '"avg_actual_return": 0.03' in params["calibration_summary_json"]
    conn.commit.assert_called()

    cursor.description = [("model_run_id",), ("sample_size",)]
    cursor.fetchall.return_value = [("run-1", 12)]
    assert repo.list_results("run-1") == [{"model_run_id": "run-1", "sample_size": 12}]


def test_prediction_repositories_require_identity_fields() -> None:
    prediction_repo = PredictionRepository(_build_mysql_mock()[0])
    backtest_repo = BacktestRepository(_build_mysql_mock()[0])

    with pytest.raises(ValueError):
        prediction_repo.upsert_model_run({"model_run_id": "run-1"})
    with pytest.raises(ValueError):
        prediction_repo.upsert_prediction({"model_run_id": "run-1", "symbol": "AAPL"})
    with pytest.raises(ValueError):
        backtest_repo.create_result({"model_run_id": "run-1"})
