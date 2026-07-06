"""Transparent prediction and backtest transport models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(slots=True)
class ModelRun:
    """Metadata for one model training or refresh run."""

    model_run_id: str
    model_name: str
    model_type: str
    model_version: str
    target_type: str
    horizon_days: int
    training_started_at: datetime | None = None
    training_completed_at: datetime | None = None
    training_window_start: date | None = None
    training_window_end: date | None = None
    feature_set_version: str | None = None
    status: str = "PENDING"
    quality_summary_json: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


@dataclass(slots=True)
class PredictionResult:
    """Prediction output with transparency fields and no execution semantics."""

    model_run_id: str
    symbol: str
    prediction_as_of: date
    horizon_days: int
    target_type: str
    prediction_id: int | None = None
    direction: str | None = None
    return_class: str | None = None
    expected_return: float | None = None
    confidence: float | None = None
    uncertainty: float | None = None
    model_quality_score: float | None = None
    input_refreshed_at: datetime | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class BacktestResult:
    """Backtest quality metrics and caveats for a model run."""

    model_run_id: str
    horizon_days: int
    backtest_id: int | None = None
    evaluation_start: date | None = None
    evaluation_end: date | None = None
    sample_size: int | None = None
    accuracy: float | None = None
    precision_score: float | None = None
    recall_score: float | None = None
    mean_absolute_error: float | None = None
    calibration_summary_json: dict[str, Any] = field(default_factory=dict)
    caveats_text: str | None = None
    created_at: datetime | None = None
