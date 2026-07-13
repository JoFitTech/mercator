"""Deterministische Prediction-Modelle fuer Stock-Analyse-Daten."""

from __future__ import annotations

from datetime import UTC, date, datetime
from math import sqrt
from typing import Any

from src.db.repositories.data_quality_repository import DataQualityRepository
from src.db.repositories.feature_repository import FundamentalFeatureRepository, TechnicalFeatureRepository
from src.db.repositories.prediction_repository import PredictionRepository
from src.db.repositories.watchlist_repository import WatchlistRepository
from src.models.prediction import ModelRun, PredictionResult
from src.models.watchlist import DataQualityIssue


class PredictionModelService:
    """Trainiert einfache transparente Modelle und erzeugt Watchlist-Prognosen."""

    FEATURE_SET_VERSION = "features-v1"
    DEFAULT_MODEL_VERSION = "v1"
    DEFAULT_TARGET_TYPE = "expected_return"

    def __init__(
        self,
        prediction_repository: PredictionRepository,
        technical_feature_repository: TechnicalFeatureRepository,
        fundamental_feature_repository: FundamentalFeatureRepository,
        watchlist_repository: WatchlistRepository,
        data_quality_repository: DataQualityRepository | None = None,
    ) -> None:
        self.prediction_repository = prediction_repository
        self.technical_feature_repository = technical_feature_repository
        self.fundamental_feature_repository = fundamental_feature_repository
        self.watchlist_repository = watchlist_repository
        self.data_quality_repository = data_quality_repository

    @staticmethod
    def _symbol(value: Any) -> str:
        return str(value or "").strip().upper()

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    @staticmethod
    def _model_type(model_name: str) -> str:
        normalized = model_name.strip().lower()
        return "ADVANCED" if normalized in {"advanced", "advanced_feature_model", "weighted_feature_model"} else "BASELINE"

    @staticmethod
    def _run_id(model_name: str, horizon_days: int, target_type: str, created_at: datetime) -> str:
        safe_name = model_name.strip().lower().replace(" ", "_") or "baseline"
        timestamp = created_at.strftime("%Y%m%d%H%M%S")
        return f"{safe_name}-{target_type}-{horizon_days}d-{timestamp}"

    def train_model(self, model_name: str, horizon_days: int, target_type: str = DEFAULT_TARGET_TYPE) -> ModelRun:
        if horizon_days <= 0:
            raise ValueError("horizon_days must be positive.")
        started_at = datetime.now(UTC)
        symbols = [self._symbol(item.get("symbol")) for item in self.watchlist_repository.list_items(active_only=True)]
        symbols = [symbol for symbol in symbols if symbol]
        ready_symbols = 0
        feature_dates: list[date] = []
        for symbol in symbols:
            technical = self.technical_feature_repository.get_latest(symbol)
            fundamental = self.fundamental_feature_repository.get_latest(symbol)
            if self._is_ready_feature(technical) and self._is_ready_feature(fundamental):
                ready_symbols += 1
                if isinstance(technical.get("feature_date"), date):
                    feature_dates.append(technical["feature_date"])

        quality_score = self._clamp(ready_symbols / max(1, len(symbols)), 0.0, 1.0)
        status = "READY" if ready_symbols > 0 else "INCOMPLETE"
        error_message = None if ready_symbols > 0 else "No watchlist symbols with ready technical and fundamental features."
        completed_at = datetime.now(UTC)
        run = ModelRun(
            model_run_id=self._run_id(model_name, horizon_days, target_type, completed_at),
            model_name=model_name.strip() or "baseline",
            model_type=self._model_type(model_name),
            model_version=self.DEFAULT_MODEL_VERSION,
            target_type=target_type,
            horizon_days=horizon_days,
            training_started_at=started_at,
            training_completed_at=completed_at,
            training_window_start=min(feature_dates) if feature_dates else None,
            training_window_end=max(feature_dates) if feature_dates else None,
            feature_set_version=self.FEATURE_SET_VERSION,
            status=status,
            quality_summary_json={
                "ready_symbols": ready_symbols,
                "symbols_seen": len(symbols),
                "quality_score": quality_score,
                "method": "deterministic_pandas_feature_heuristic",
            },
            error_message=error_message,
        )
        self.prediction_repository.upsert_model_run(run)
        if run.status == "READY" and hasattr(self.prediction_repository, "mark_obsolete_versions"):
            self.prediction_repository.mark_obsolete_versions(
                model_name=run.model_name,
                horizon_days=run.horizon_days,
                target_type=run.target_type,
                keep_model_run_id=run.model_run_id,
            )
        return run

    def predict_watchlist(self, model_run_id: str) -> list[PredictionResult]:
        model_run = self.prediction_repository.get_model_run(model_run_id)
        if not model_run:
            raise ValueError(f"Unknown model_run_id: {model_run_id}")
        if str(model_run.get("status") or "").upper() != "READY":
            return []

        predictions: list[PredictionResult] = []
        for item in self.watchlist_repository.list_items(active_only=True):
            symbol = self._symbol(item.get("symbol"))
            if not symbol:
                continue
            technical = self.technical_feature_repository.get_latest(symbol)
            fundamental = self.fundamental_feature_repository.get_latest(symbol)
            if not self._is_ready_feature(technical) or not self._is_ready_feature(fundamental):
                self._record_quality_issue(symbol, "Insufficient ready features for prediction.")
                continue
            predictions.append(self._build_prediction(model_run, technical, fundamental))
        self.prediction_repository.upsert_predictions(predictions)
        return predictions

    @staticmethod
    def _is_ready_feature(feature: dict[str, Any] | None) -> bool:
        return bool(feature) and str(feature.get("feature_status") or "").upper() == "READY"

    def _build_prediction(
        self,
        model_run: dict[str, Any],
        technical: dict[str, Any],
        fundamental: dict[str, Any],
    ) -> PredictionResult:
        model_type = str(model_run.get("model_type") or "BASELINE").upper()
        expected_return = (
            self._advanced_expected_return(technical, fundamental)
            if model_type == "ADVANCED"
            else self._baseline_expected_return(technical)
        )
        uncertainty = self._uncertainty(technical, int(model_run["horizon_days"]))
        quality_score = self._quality_score(model_run)
        confidence = self._clamp(0.35 + (quality_score * 0.35) + (max(0.0, abs(expected_return)) * 1.5) - uncertainty, 0.05, 0.95)
        return PredictionResult(
            model_run_id=str(model_run["model_run_id"]),
            symbol=str(technical["symbol"]).upper(),
            prediction_as_of=technical["feature_date"],
            horizon_days=int(model_run["horizon_days"]),
            target_type=str(model_run.get("target_type") or self.DEFAULT_TARGET_TYPE),
            direction=self._direction(expected_return),
            return_class=self._return_class(expected_return),
            expected_return=expected_return,
            confidence=confidence,
            uncertainty=uncertainty,
            model_quality_score=quality_score,
            input_refreshed_at=self._max_datetime(technical.get("input_refreshed_at"), fundamental.get("input_refreshed_at")),
        )

    def _baseline_expected_return(self, technical: dict[str, Any]) -> float:
        momentum_1m = self._to_float(technical.get("momentum_1m"))
        momentum_3m = self._to_float(technical.get("momentum_3m"))
        return self._clamp((momentum_1m * 0.45) + (momentum_3m * 0.55), -0.50, 0.50)

    def _advanced_expected_return(self, technical: dict[str, Any], fundamental: dict[str, Any]) -> float:
        momentum_1m = self._to_float(technical.get("momentum_1m"))
        momentum_3m = self._to_float(technical.get("momentum_3m"))
        momentum_6m = self._to_float(technical.get("momentum_6m"))
        revenue_growth = self._to_float(fundamental.get("revenue_growth"))
        gross_margin = self._to_float(fundamental.get("gross_margin"))
        valuation_ratio = self._to_float(fundamental.get("valuation_ratio"), default=25.0)
        debt_to_equity = self._to_float(fundamental.get("debt_to_equity"))
        volume_trend = self._to_float(technical.get("volume_trend_20d"))
        valuation_penalty = max(0.0, (valuation_ratio - 25.0) / 100.0)
        debt_penalty = max(0.0, debt_to_equity / 25.0)
        score = (
            (momentum_1m * 0.20)
            + (momentum_3m * 0.25)
            + (momentum_6m * 0.15)
            + (revenue_growth * 0.15)
            + (gross_margin * 0.10)
            + (volume_trend * 0.05)
            - (valuation_penalty * 0.05)
            - (debt_penalty * 0.05)
        )
        return self._clamp(score, -0.50, 0.50)

    def _uncertainty(self, technical: dict[str, Any], horizon_days: int) -> float:
        volatility = self._to_float(technical.get("volatility_20d"), default=0.02)
        scaled = volatility * sqrt(max(1, horizon_days))
        return self._clamp(scaled, 0.05, 0.85)

    def _quality_score(self, model_run: dict[str, Any]) -> float:
        summary = model_run.get("quality_summary_json") or {}
        if isinstance(summary, str):
            return 0.65
        return self._clamp(self._to_float(summary.get("quality_score"), default=0.65), 0.0, 1.0)

    @staticmethod
    def _direction(expected_return: float) -> str:
        if expected_return >= 0.02:
            return "POSITIVE"
        if expected_return <= -0.02:
            return "NEGATIVE"
        return "NEUTRAL"

    @staticmethod
    def _return_class(expected_return: float) -> str:
        if expected_return >= 0.05:
            return "HIGH"
        if expected_return >= 0.02:
            return "MODERATE"
        if expected_return <= -0.05:
            return "LOW"
        return "FLAT"

    @staticmethod
    def _max_datetime(left: Any, right: Any) -> datetime | None:
        values = [value for value in (left, right) if isinstance(value, datetime)]
        return max(values) if values else None

    def _record_quality_issue(self, symbol: str, message: str) -> None:
        if self.data_quality_repository is None:
            return
        self.data_quality_repository.create_issue(
            DataQualityIssue(
                symbol=symbol,
                data_category="prediction",
                severity="WARNING",
                status="OPEN",
                message=message,
                detected_at=datetime.now(UTC),
            )
        )
