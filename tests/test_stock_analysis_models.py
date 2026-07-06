"""Contract tests for foundational stock-analysis transport models."""

from __future__ import annotations

from datetime import date, datetime


def test_raw_provider_response_preserves_failed_payload_metadata() -> None:
    from src.models.stock import RawProviderResponse

    response = RawProviderResponse(
        provider="fmp",
        category="company_profile",
        request_hash="abc123",
        status="FAILED",
        fetched_at=datetime(2026, 1, 1, 12, 0, 0),
        symbol="AAPL",
        error_message="rate limited",
    )

    assert response.provider == "fmp"
    assert response.status == "FAILED"
    assert response.payload == {}
    assert response.request_params == {}
    assert response.error_message == "rate limited"


def test_import_run_summary_tracks_raw_before_clean_counts() -> None:
    from src.models.stock import ImportRunSummary

    summary = ImportRunSummary(
        import_run_id="run-1",
        provider="fmp",
        import_type="watchlist",
        started_at=datetime(2026, 1, 1, 12, 0, 0),
        status="PARTIAL",
        symbols_requested=3,
        symbols_succeeded=2,
        symbols_failed=1,
        raw_responses_written=3,
        clean_records_written=2,
    )

    assert summary.raw_responses_written >= summary.clean_records_written
    assert summary.status == "PARTIAL"


def test_watchlist_item_keeps_unresolved_symbols_visible() -> None:
    from src.models.watchlist import WatchlistItem

    item = WatchlistItem(symbol="UNRESOLVED", active=True)

    assert item.symbol == "UNRESOLVED"
    assert item.active is True
    assert item.resolution_status == "UNRESOLVED"


def test_data_quality_issue_uses_text_status_fields() -> None:
    from src.models.watchlist import DataQualityIssue

    issue = DataQualityIssue(
        symbol="AAPL",
        data_category="company_profile",
        severity="WARNING",
        status="OPEN",
        message="Profile data is stale",
        detected_at=datetime(2026, 1, 1, 12, 0, 0),
    )

    assert issue.message == "Profile data is stale"
    assert issue.status == "OPEN"


def test_feature_models_capture_unavailable_reasons() -> None:
    from src.models.features import FundamentalFeatures, TechnicalFeatures

    technical = TechnicalFeatures(
        symbol="AAPL",
        feature_date=date(2026, 1, 1),
        feature_status="UNAVAILABLE",
        unavailable_reason="Not enough price history",
    )
    fundamental = FundamentalFeatures(
        symbol="AAPL",
        feature_period=date(2026, 1, 1),
        feature_status="UNAVAILABLE",
        unavailable_reason="Missing fundamentals",
    )

    assert technical.unavailable_reason == "Not enough price history"
    assert fundamental.unavailable_reason == "Missing fundamentals"


def test_prediction_and_backtest_models_are_transparent_only() -> None:
    from src.models.prediction import BacktestResult, ModelRun, PredictionResult

    run = ModelRun(
        model_run_id="model-run-1",
        model_name="baseline",
        model_type="baseline",
        model_version="v1",
        target_type="return",
        horizon_days=20,
    )
    prediction = PredictionResult(
        model_run_id=run.model_run_id,
        symbol="AAPL",
        prediction_as_of=date(2026, 1, 1),
        horizon_days=20,
        target_type="return",
        confidence=0.7,
        uncertainty=0.3,
        model_quality_score=0.6,
    )
    backtest = BacktestResult(model_run_id=run.model_run_id, horizon_days=20)

    assert prediction.confidence == 0.7
    assert prediction.uncertainty == 0.3
    assert prediction.model_quality_score == 0.6
    assert backtest.caveats_text is None
    assert not hasattr(prediction, "order_action")
    assert not hasattr(prediction, "trade_execution")


def test_preference_score_uses_ranking_not_trade_execution_language() -> None:
    from src.models.preference import PreferenceScore

    score = PreferenceScore(
        symbol="AAPL",
        score_as_of=date(2026, 1, 1),
        preference_score=0.75,
        rank_position=1,
        explanation_positive="Strong quality and momentum",
        data_quality_summary="Ready",
    )

    assert score.preference_score == 0.75
    assert score.rank_position == 1
    assert not hasattr(score, "buy_signal")
    assert not hasattr(score, "order_action")
