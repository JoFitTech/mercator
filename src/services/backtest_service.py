"""Backtest-Auswertung fuer gespeicherte Prediction-Ergebnisse."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from src.db.repositories.backtest_repository import BacktestRepository
from src.db.repositories.prediction_repository import PredictionRepository
from src.db.repositories.stock_price_repository import StockPriceRepository
from src.models.prediction import BacktestResult


class BacktestService:
    """Vergleicht Prediction-Ergebnisse mit nachgelagerten Kurs-Outcomes."""

    MIN_SAMPLE_SIZE = 5

    def __init__(
        self,
        prediction_repository: PredictionRepository,
        price_repository: StockPriceRepository,
        backtest_repository: BacktestRepository,
    ) -> None:
        self.prediction_repository = prediction_repository
        self.price_repository = price_repository
        self.backtest_repository = backtest_repository

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _row_date(row: dict[str, Any]) -> date | None:
        value = row.get("price_date") or row.get("date")
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
        return None

    def backtest_model(self, model_run_id: str) -> BacktestResult:
        model_run = self.prediction_repository.get_model_run(model_run_id)
        if not model_run:
            raise ValueError(f"Unknown model_run_id: {model_run_id}")
        predictions = self.prediction_repository.list_predictions(model_run_id=model_run_id, limit=5000)
        evaluated = [sample for sample in (self._evaluate_prediction(prediction) for prediction in predictions) if sample]

        if not evaluated:
            result = BacktestResult(
                model_run_id=model_run_id,
                horizon_days=int(model_run["horizon_days"]),
                sample_size=0,
                calibration_summary_json={"evaluated_predictions": 0},
                caveats_text="No predictions had enough future price history for backtesting.",
            )
            result.backtest_id = self.backtest_repository.create_result(result)
            return result

        actuals = [sample["actual_return"] for sample in evaluated]
        predicted = [sample["expected_return"] for sample in evaluated]
        direction_hits = [self._same_direction(pred, actual) for pred, actual in zip(predicted, actuals, strict=False)]
        positive_predictions = [sample for sample in evaluated if sample["expected_return"] > 0]
        actual_positives = [sample for sample in evaluated if sample["actual_return"] > 0]
        true_positives = [sample for sample in positive_predictions if sample["actual_return"] > 0]

        sample_size = len(evaluated)
        caveats: list[str] = []
        if sample_size < self.MIN_SAMPLE_SIZE:
            caveats.append(f"Small backtest sample ({sample_size}); treat quality metrics as directional only.")

        result = BacktestResult(
            model_run_id=model_run_id,
            horizon_days=int(model_run["horizon_days"]),
            evaluation_start=min(sample["prediction_as_of"] for sample in evaluated),
            evaluation_end=max(sample["outcome_date"] for sample in evaluated),
            sample_size=sample_size,
            accuracy=sum(direction_hits) / sample_size,
            precision_score=(len(true_positives) / len(positive_predictions)) if positive_predictions else None,
            recall_score=(len(true_positives) / len(actual_positives)) if actual_positives else None,
            mean_absolute_error=sum(abs(pred - actual) for pred, actual in zip(predicted, actuals, strict=False)) / sample_size,
            calibration_summary_json={
                "avg_predicted_return": sum(predicted) / sample_size,
                "avg_actual_return": sum(actuals) / sample_size,
                "positive_predictions": len(positive_predictions),
            },
            caveats_text=" ".join(caveats) or None,
        )
        result.backtest_id = self.backtest_repository.create_result(result)
        return result

    @staticmethod
    def _same_direction(predicted_return: float, actual_return: float) -> bool:
        if predicted_return == 0 or actual_return == 0:
            return abs(predicted_return - actual_return) < 0.01
        return (predicted_return > 0) == (actual_return > 0)

    def _evaluate_prediction(self, prediction: dict[str, Any]) -> dict[str, Any] | None:
        symbol = str(prediction.get("symbol") or "").strip().upper()
        prediction_as_of = prediction.get("prediction_as_of")
        horizon_days = int(prediction.get("horizon_days") or 0)
        expected_return = self._to_float(prediction.get("expected_return"))
        if not symbol or not isinstance(prediction_as_of, date) or horizon_days <= 0 or expected_return is None:
            return None

        prices = self.price_repository.list_prices(symbol, limit=5000)
        dated_prices = sorted(
            (
                (row_date, self._to_float(row.get("adjusted_close") or row.get("close_price") or row.get("close")))
                for row in prices
                if (row_date := self._row_date(row)) is not None
            ),
            key=lambda item: item[0],
        )
        start = next(((row_date, close) for row_date, close in dated_prices if row_date >= prediction_as_of and close), None)
        target_date = prediction_as_of + timedelta(days=horizon_days)
        end = next(((row_date, close) for row_date, close in dated_prices if row_date >= target_date and close), None)
        if start is None or end is None or not start[1]:
            return None
        actual_return = (end[1] / start[1]) - 1.0
        return {
            "prediction_as_of": prediction_as_of,
            "outcome_date": end[0],
            "expected_return": expected_return,
            "actual_return": actual_return,
        }
