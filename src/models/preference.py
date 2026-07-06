"""Transport model for transparent stock preference ranking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(slots=True)
class PreferenceScore:
    """Decision-support score with component explanations, not trade execution."""

    symbol: str
    score_as_of: date
    preference_score_id: int | None = None
    preference_score: float | None = None
    rank_position: int | None = None
    fundamental_component: float | None = None
    technical_component: float | None = None
    risk_component: float | None = None
    prediction_component: float | None = None
    confidence_component: float | None = None
    confidence: float | None = None
    uncertainty: float | None = None
    explanation_positive: str | None = None
    explanation_negative: str | None = None
    data_quality_summary: str | None = None
    created_at: datetime | None = None
