from __future__ import annotations

from datetime import date

import pytest

from src.services.dashboard_service import DashboardService
from src.services.preference_scoring_service import PreferenceScoringService


class _PreferenceRepo:
    def __init__(self) -> None:
        self.saved = []

    def upsert_scores(self, scores):
        self.saved.extend(scores)
        return len(scores)


class _FeatureRepo:
    def __init__(self, rows):
        self.rows = rows

    def get_latest(self, symbol):
        return self.rows.get(symbol)


class _PredictionRepo:
    def __init__(self, rows):
        self.rows = rows

    def list_predictions(self, symbol=None, limit=1, model_run_id=None):
        return self.rows.get(symbol, [])[:limit]


class _WatchlistRepo:
    def __init__(self, symbols):
        self.symbols = symbols

    def list_items(self, active_only: bool = True):
        return [{"symbol": symbol} for symbol in self.symbols]


def _technical(symbol: str, momentum_3m: float = 0.08, volatility: float = 0.02):
    return {
        "symbol": symbol,
        "feature_status": "READY",
        "momentum_1m": 0.04,
        "momentum_3m": momentum_3m,
        "momentum_6m": 0.10,
        "volatility_20d": volatility,
        "max_drawdown_1y": -0.12,
        "volume_trend_20d": 0.05,
    }


def _fundamental(symbol: str, revenue_growth: float = 0.12, gross_margin: float = 0.42):
    return {
        "symbol": symbol,
        "feature_status": "READY",
        "revenue_growth": revenue_growth,
        "gross_margin": gross_margin,
        "valuation_ratio": 22.0,
        "debt_to_equity": 1.0,
    }


def _prediction(symbol: str, expected_return: float = 0.05, confidence: float = 0.75):
    return {
        "symbol": symbol,
        "expected_return": expected_return,
        "confidence": confidence,
        "uncertainty": 0.12,
    }


def _service(technical_rows, fundamental_rows, prediction_rows, symbols=("AAPL",)):
    preference_repo = _PreferenceRepo()
    service = PreferenceScoringService(
        preference_repository=preference_repo,
        technical_feature_repository=_FeatureRepo(technical_rows),
        fundamental_feature_repository=_FeatureRepo(fundamental_rows),
        prediction_repository=_PredictionRepo(prediction_rows),
        watchlist_repository=_WatchlistRepo(symbols),
    )
    return service, preference_repo


def test_preference_scoring_service_scores_symbol_with_all_components() -> None:
    service, _ = _service(
        {"AAPL": _technical("AAPL")},
        {"AAPL": _fundamental("AAPL")},
        {"AAPL": [_prediction("AAPL")]},
    )

    score = service.score_symbol("aapl", date(2026, 7, 10))

    assert score.symbol == "AAPL"
    assert score.preference_score > 60
    assert score.fundamental_component > 60
    assert score.technical_component > 60
    assert score.prediction_component > 60
    assert score.confidence == 0.75
    assert "Preference supported by" in score.explanation_positive
    assert "All required scoring inputs" in score.data_quality_summary


def test_preference_scoring_service_ranks_watchlist_and_persists_positions() -> None:
    service, preference_repo = _service(
        {
            "AAPL": _technical("AAPL", momentum_3m=0.12),
            "MSFT": _technical("MSFT", momentum_3m=-0.05),
        },
        {
            "AAPL": _fundamental("AAPL", revenue_growth=0.16),
            "MSFT": _fundamental("MSFT", revenue_growth=0.02, gross_margin=0.25),
        },
        {
            "AAPL": [_prediction("AAPL", expected_return=0.08, confidence=0.8)],
            "MSFT": [_prediction("MSFT", expected_return=-0.02, confidence=0.45)],
        },
        symbols=("MSFT", "AAPL"),
    )

    rankings = service.rank_watchlist(date(2026, 7, 10))

    assert [score.symbol for score in rankings] == ["AAPL", "MSFT"]
    assert [score.rank_position for score in rankings] == [1, 2]
    assert preference_repo.saved == rankings


def test_preference_scoring_service_penalizes_missing_prediction_with_warning() -> None:
    service, _ = _service(
        {"AAPL": _technical("AAPL")},
        {"AAPL": _fundamental("AAPL")},
        {"AAPL": []},
    )

    score = service.score_symbol("AAPL", date(2026, 7, 10))

    assert score.prediction_component == 35.0
    assert score.confidence_component == 35.0
    assert "no prediction is available" in score.data_quality_summary
    assert "data-quality warnings" in score.explanation_negative


def test_preference_scoring_service_explains_conflicting_signals_without_execution_language() -> None:
    service, _ = _service(
        {"AAPL": _technical("AAPL", momentum_3m=-0.30, volatility=0.08)},
        {"AAPL": _fundamental("AAPL", revenue_growth=0.25, gross_margin=0.55)},
        {"AAPL": [_prediction("AAPL", expected_return=0.01, confidence=0.4)]},
    )

    score = service.score_symbol("AAPL", date(2026, 7, 10))
    combined_text = f"{score.explanation_positive} {score.explanation_negative}".lower()

    assert "solid fundamentals" in combined_text
    assert "weak technical setup" in combined_text
    forbidden_terms = ("buy recommendation", "order", "execution", "trade decision")
    assert not any(term in combined_text for term in forbidden_terms)


def test_preference_scoring_service_rejects_empty_symbol() -> None:
    service, _ = _service({}, {}, {})
    with pytest.raises(ValueError):
        service.score_symbol("", date(2026, 7, 10))


def test_dashboard_service_loads_preference_ranking_summaries() -> None:
    class _PreferenceRankingRepo:
        def list_rankings(self, limit=25):
            return [{"symbol": "AAPL", "rank_position": 1, "preference_score": 82.5}]

    service = DashboardService(
        raw_repo=None,
        company_mongo_repo=None,
        trade_repo=object(),
        company_repo=object(),
        preference_score_repo=_PreferenceRankingRepo(),
    )

    assert service._load_preference_rankings() == [{"symbol": "AAPL", "rank_position": 1, "preference_score": 82.5}]
