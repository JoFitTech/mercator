"""Transparentes Preference Scoring fuer Watchlist-Rankings."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.db.repositories.feature_repository import FundamentalFeatureRepository, TechnicalFeatureRepository
from src.db.repositories.prediction_repository import PredictionRepository
from src.db.repositories.preference_score_repository import PreferenceScoreRepository
from src.db.repositories.watchlist_repository import WatchlistRepository
from src.models.preference import PreferenceScore


class PreferenceScoringService:
    """Kombiniert Features und Predictions zu erklaerbaren Preference Scores."""

    WEIGHTS = {
        "fundamental": 0.25,
        "technical": 0.25,
        "risk": 0.15,
        "prediction": 0.25,
        "confidence": 0.10,
    }
    MISSING_COMPONENT_SCORE = 35.0

    def __init__(
        self,
        preference_repository: PreferenceScoreRepository,
        technical_feature_repository: TechnicalFeatureRepository,
        fundamental_feature_repository: FundamentalFeatureRepository,
        prediction_repository: PredictionRepository,
        watchlist_repository: WatchlistRepository,
    ) -> None:
        self.preference_repository = preference_repository
        self.technical_feature_repository = technical_feature_repository
        self.fundamental_feature_repository = fundamental_feature_repository
        self.prediction_repository = prediction_repository
        self.watchlist_repository = watchlist_repository

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
    def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
        return max(low, min(high, value))

    def score_symbol(self, symbol: str, as_of: date) -> PreferenceScore:
        normalized_symbol = self._symbol(symbol)
        if not normalized_symbol:
            raise ValueError("Preference scoring requires a symbol.")

        technical = self.technical_feature_repository.get_latest(normalized_symbol)
        fundamental = self.fundamental_feature_repository.get_latest(normalized_symbol)
        prediction = self._latest_prediction(normalized_symbol)
        warnings: list[str] = []

        fundamental_component = self._fundamental_component(fundamental, warnings)
        technical_component = self._technical_component(technical, warnings)
        risk_component = self._risk_component(technical, fundamental, warnings)
        prediction_component = self._prediction_component(prediction, warnings)
        confidence_component = self._confidence_component(prediction, warnings)

        preference_score = (
            fundamental_component * self.WEIGHTS["fundamental"]
            + technical_component * self.WEIGHTS["technical"]
            + risk_component * self.WEIGHTS["risk"]
            + prediction_component * self.WEIGHTS["prediction"]
            + confidence_component * self.WEIGHTS["confidence"]
        )
        confidence = self._to_float(prediction.get("confidence"), default=0.0) if prediction else None
        uncertainty = self._to_float(prediction.get("uncertainty"), default=0.0) if prediction else None
        score = PreferenceScore(
            symbol=normalized_symbol,
            score_as_of=as_of,
            preference_score=round(self._clamp(preference_score), 6),
            fundamental_component=round(fundamental_component, 6),
            technical_component=round(technical_component, 6),
            risk_component=round(risk_component, 6),
            prediction_component=round(prediction_component, 6),
            confidence_component=round(confidence_component, 6),
            confidence=confidence,
            uncertainty=uncertainty,
            explanation_positive=self._positive_explanation(
                fundamental_component,
                technical_component,
                prediction_component,
                confidence_component,
            ),
            explanation_negative=self._negative_explanation(
                fundamental_component,
                technical_component,
                risk_component,
                prediction_component,
                warnings,
            ),
            data_quality_summary="; ".join(warnings) if warnings else "All required scoring inputs are available.",
        )
        return score

    def rank_watchlist(self, as_of: date) -> list[PreferenceScore]:
        scores: list[PreferenceScore] = []
        for item in self.watchlist_repository.list_items(active_only=True):
            symbol = self._symbol(item.get("symbol"))
            if symbol:
                scores.append(self.score_symbol(symbol, as_of))
        scores.sort(key=lambda score: (score.preference_score or 0.0, score.symbol), reverse=True)
        for index, score in enumerate(scores, start=1):
            score.rank_position = index
        self.preference_repository.upsert_scores(scores)
        return scores

    def _latest_prediction(self, symbol: str) -> dict[str, Any] | None:
        predictions = self.prediction_repository.list_predictions(symbol=symbol, limit=1)
        return predictions[0] if predictions else None

    @staticmethod
    def _feature_ready(feature: dict[str, Any] | None) -> bool:
        return bool(feature) and str(feature.get("feature_status") or "").upper() == "READY"

    def _fundamental_component(self, feature: dict[str, Any] | None, warnings: list[str]) -> float:
        if not self._feature_ready(feature):
            warnings.append("Fundamental component uses conservative fallback because ready fundamentals are missing.")
            return self.MISSING_COMPONENT_SCORE
        revenue = self._to_float(feature.get("revenue_growth"))
        margin = self._to_float(feature.get("gross_margin"))
        valuation = self._to_float(feature.get("valuation_ratio"), default=25.0)
        debt = self._to_float(feature.get("debt_to_equity"))
        revenue_score = self._clamp(50.0 + revenue * 180.0)
        margin_score = self._clamp(margin * 140.0)
        valuation_score = self._clamp(90.0 - max(0.0, valuation - 15.0) * 2.0)
        debt_score = self._clamp(85.0 - debt * 10.0)
        return (revenue_score * 0.35) + (margin_score * 0.25) + (valuation_score * 0.20) + (debt_score * 0.20)

    def _technical_component(self, feature: dict[str, Any] | None, warnings: list[str]) -> float:
        if not self._feature_ready(feature):
            warnings.append("Technical component uses conservative fallback because ready technicals are missing.")
            return self.MISSING_COMPONENT_SCORE
        m1 = self._to_float(feature.get("momentum_1m"))
        m3 = self._to_float(feature.get("momentum_3m"))
        m6 = self._to_float(feature.get("momentum_6m"))
        volume = self._to_float(feature.get("volume_trend_20d"))
        return self._clamp(50.0 + (m1 * 120.0) + (m3 * 90.0) + (m6 * 60.0) + (volume * 15.0))

    def _risk_component(self, technical: dict[str, Any] | None, fundamental: dict[str, Any] | None, warnings: list[str]) -> float:
        if not self._feature_ready(technical):
            warnings.append("Risk component uses conservative fallback because volatility/drawdown data is missing.")
            return self.MISSING_COMPONENT_SCORE
        volatility = self._to_float(technical.get("volatility_20d"), default=0.05)
        drawdown = abs(self._to_float(technical.get("max_drawdown_1y")))
        debt = self._to_float(fundamental.get("debt_to_equity"), default=1.0) if fundamental else 1.0
        return self._clamp(90.0 - (volatility * 260.0) - (drawdown * 90.0) - (debt * 4.0))

    def _prediction_component(self, prediction: dict[str, Any] | None, warnings: list[str]) -> float:
        if not prediction:
            warnings.append("Prediction component uses conservative fallback because no prediction is available.")
            return self.MISSING_COMPONENT_SCORE
        expected_return = self._to_float(prediction.get("expected_return"))
        return self._clamp(50.0 + expected_return * 450.0)

    def _confidence_component(self, prediction: dict[str, Any] | None, warnings: list[str]) -> float:
        if not prediction:
            warnings.append("Confidence component uses conservative fallback because no prediction confidence is available.")
            return self.MISSING_COMPONENT_SCORE
        confidence = self._to_float(prediction.get("confidence"), default=0.0)
        uncertainty = self._to_float(prediction.get("uncertainty"), default=0.0)
        return self._clamp((confidence * 100.0) - (uncertainty * 35.0))

    @staticmethod
    def _positive_explanation(
        fundamental_component: float,
        technical_component: float,
        prediction_component: float,
        confidence_component: float,
    ) -> str:
        strengths: list[str] = []
        if fundamental_component >= 60:
            strengths.append("solid fundamentals")
        if technical_component >= 60:
            strengths.append("supportive technical trend")
        if prediction_component >= 60:
            strengths.append("positive prediction output")
        if confidence_component >= 60:
            strengths.append("useful model confidence")
        if not strengths:
            return "No strong positive component dominates this preference score."
        return "Preference supported by " + ", ".join(strengths) + "."

    @staticmethod
    def _negative_explanation(
        fundamental_component: float,
        technical_component: float,
        risk_component: float,
        prediction_component: float,
        warnings: list[str],
    ) -> str:
        concerns: list[str] = []
        if fundamental_component < 45:
            concerns.append("weak or incomplete fundamentals")
        if technical_component < 45:
            concerns.append("weak technical setup")
        if risk_component < 45:
            concerns.append("elevated risk inputs")
        if prediction_component < 45:
            concerns.append("weak or missing prediction output")
        if warnings:
            concerns.append("data-quality warnings")
        if not concerns:
            return "No major deprioritizing component is visible."
        return "Preference reduced by " + ", ".join(concerns) + "."
