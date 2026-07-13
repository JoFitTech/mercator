from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone

import pytest

from src.services.prediction_model_service import PredictionModelService


class _PredictionRepo:
    def __init__(self) -> None:
        self.runs = {}
        self.predictions = []

    def upsert_model_run(self, run):
        self.runs[run.model_run_id] = run
        return run.model_run_id

    def get_model_run(self, model_run_id):
        run = self.runs.get(model_run_id)
        if isinstance(run, dict):
            return run
        return asdict(run) if run else None

    def upsert_predictions(self, predictions):
        self.predictions.extend(predictions)
        return len(predictions)


class _FeatureRepo:
    def __init__(self, rows):
        self.rows = rows

    def get_latest(self, symbol):
        return self.rows.get(symbol)


class _WatchlistRepo:
    def __init__(self, symbols):
        self.symbols = symbols

    def list_items(self, active_only: bool = True):
        return [{"symbol": symbol} for symbol in self.symbols]


class _DataQualityRepo:
    def __init__(self) -> None:
        self.issues = []

    def create_issue(self, issue):
        self.issues.append(issue)
        return len(self.issues)


def _technical(symbol: str, status: str = "READY"):
    return {
        "symbol": symbol,
        "feature_date": date(2026, 7, 9),
        "momentum_1m": 0.04,
        "momentum_3m": 0.08,
        "momentum_6m": 0.12,
        "volatility_20d": 0.02,
        "volume_trend_20d": 0.10,
        "feature_status": status,
        "input_refreshed_at": datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc),
    }


def _fundamental(symbol: str, status: str = "READY"):
    return {
        "symbol": symbol,
        "feature_period": date(2025, 12, 31),
        "revenue_growth": 0.13,
        "gross_margin": 0.42,
        "valuation_ratio": 24.0,
        "debt_to_equity": 1.2,
        "market_cap": 1_000_000_000,
        "feature_status": status,
        "input_refreshed_at": datetime(2026, 7, 9, 11, 0, tzinfo=timezone.utc),
    }


def _service(technical_rows, fundamental_rows, symbols=("AAPL",)):
    prediction_repo = _PredictionRepo()
    dq_repo = _DataQualityRepo()
    service = PredictionModelService(
        prediction_repository=prediction_repo,
        technical_feature_repository=_FeatureRepo(technical_rows),
        fundamental_feature_repository=_FeatureRepo(fundamental_rows),
        watchlist_repository=_WatchlistRepo(symbols),
        data_quality_repository=dq_repo,
    )
    return service, prediction_repo, dq_repo


def test_prediction_model_service_trains_ready_baseline_model() -> None:
    service, prediction_repo, _ = _service({"AAPL": _technical("AAPL")}, {"AAPL": _fundamental("AAPL")})

    run = service.train_model("baseline", horizon_days=20)

    assert run.status == "READY"
    assert run.model_type == "BASELINE"
    assert run.quality_summary_json["ready_symbols"] == 1
    assert prediction_repo.runs[run.model_run_id].target_type == "expected_return"


def test_prediction_model_service_generates_transparent_predictions() -> None:
    service, prediction_repo, dq_repo = _service({"AAPL": _technical("AAPL")}, {"AAPL": _fundamental("AAPL")})
    run = service.train_model("advanced", horizon_days=20)

    predictions = service.predict_watchlist(run.model_run_id)

    assert len(predictions) == 1
    prediction = predictions[0]
    assert prediction.symbol == "AAPL"
    assert prediction.direction == "POSITIVE"
    assert prediction.expected_return is not None
    assert prediction.confidence is not None
    assert prediction.uncertainty is not None
    assert prediction.model_quality_score == 1.0
    assert prediction.input_refreshed_at == datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    assert prediction_repo.predictions == predictions
    assert dq_repo.issues == []


def test_prediction_model_service_records_issue_for_insufficient_features() -> None:
    service, _, dq_repo = _service({"MSFT": _technical("MSFT", status="INCOMPLETE")}, {"MSFT": _fundamental("MSFT")}, symbols=("MSFT",))
    run = service.train_model("baseline", horizon_days=20)

    assert run.status == "INCOMPLETE"
    assert service.predict_watchlist(run.model_run_id) == []
    assert dq_repo.issues == []

    ready_run = asdict(run)
    ready_run["status"] = "READY"
    service.prediction_repository.runs[run.model_run_id] = ready_run
    assert service.predict_watchlist(run.model_run_id) == []
    assert dq_repo.issues[0].data_category == "prediction"


def test_prediction_model_service_rejects_unknown_model_run() -> None:
    service, _, _ = _service({}, {})
    with pytest.raises(ValueError):
        service.predict_watchlist("missing-run")
