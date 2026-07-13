from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.services.backtest_service import BacktestService


class _PredictionRepo:
    def __init__(self, model_run=None, predictions=None) -> None:
        self.model_run = model_run
        self.predictions = predictions or []

    def get_model_run(self, model_run_id):
        return self.model_run if self.model_run and self.model_run["model_run_id"] == model_run_id else None

    def list_predictions(self, model_run_id=None, limit=100):
        return self.predictions


class _PriceRepo:
    def __init__(self, rows_by_symbol):
        self.rows_by_symbol = rows_by_symbol

    def list_prices(self, symbol, limit=5000):
        return self.rows_by_symbol.get(symbol, [])


class _BacktestRepo:
    def __init__(self) -> None:
        self.saved = []

    def create_result(self, result):
        self.saved.append(result)
        return len(self.saved)


def _price_rows(start: date, values: list[float]):
    return [
        {"price_date": start + timedelta(days=index), "close_price": value, "adjusted_close": value}
        for index, value in enumerate(values)
    ]


def test_backtest_service_calculates_quality_metrics_and_caveats() -> None:
    model_run = {"model_run_id": "run-1", "horizon_days": 2}
    predictions = [
        {
            "model_run_id": "run-1",
            "symbol": "AAPL",
            "prediction_as_of": date(2026, 1, 1),
            "horizon_days": 2,
            "expected_return": 0.10,
        },
        {
            "model_run_id": "run-1",
            "symbol": "MSFT",
            "prediction_as_of": date(2026, 1, 1),
            "horizon_days": 2,
            "expected_return": -0.05,
        },
    ]
    backtest_repo = _BacktestRepo()
    service = BacktestService(
        prediction_repository=_PredictionRepo(model_run, predictions),
        price_repository=_PriceRepo(
            {
                "AAPL": _price_rows(date(2026, 1, 1), [100, 102, 112]),
                "MSFT": _price_rows(date(2026, 1, 1), [100, 99, 90]),
            }
        ),
        backtest_repository=backtest_repo,
    )

    result = service.backtest_model("run-1")

    assert result.backtest_id == 1
    assert result.sample_size == 2
    assert result.accuracy == 1.0
    assert result.precision_score == 1.0
    assert result.recall_score == 1.0
    assert round(result.mean_absolute_error, 3) == 0.035
    assert "Small backtest sample" in result.caveats_text
    assert backtest_repo.saved[0] == result


def test_backtest_service_records_no_history_caveat() -> None:
    model_run = {"model_run_id": "run-1", "horizon_days": 20}
    prediction = {
        "model_run_id": "run-1",
        "symbol": "AAPL",
        "prediction_as_of": date(2026, 1, 1),
        "horizon_days": 20,
        "expected_return": 0.10,
    }
    service = BacktestService(
        prediction_repository=_PredictionRepo(model_run, [prediction]),
        price_repository=_PriceRepo({"AAPL": _price_rows(date(2026, 1, 1), [100, 101])}),
        backtest_repository=_BacktestRepo(),
    )

    result = service.backtest_model("run-1")

    assert result.sample_size == 0
    assert "No predictions had enough future price history" in result.caveats_text


def test_backtest_service_rejects_unknown_model_run() -> None:
    service = BacktestService(
        prediction_repository=_PredictionRepo(),
        price_repository=_PriceRepo({}),
        backtest_repository=_BacktestRepo(),
    )
    with pytest.raises(ValueError):
        service.backtest_model("missing-run")
