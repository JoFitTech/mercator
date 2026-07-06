"""Transport models for calculated stock-analysis features."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(slots=True)
class TechnicalFeatures:
    """Calculated price and volume features for one symbol/date."""

    symbol: str
    feature_date: date
    momentum_1m: float | None = None
    momentum_3m: float | None = None
    momentum_6m: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    volatility_20d: float | None = None
    max_drawdown_1y: float | None = None
    volume_trend_20d: float | None = None
    feature_status: str = "UNKNOWN"
    unavailable_reason: str | None = None
    input_refreshed_at: datetime | None = None


@dataclass(slots=True)
class FundamentalFeatures:
    """Calculated fundamental features for one symbol/period."""

    symbol: str
    feature_period: date
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    valuation_ratio: float | None = None
    debt_to_equity: float | None = None
    market_cap: int | None = None
    feature_status: str = "UNKNOWN"
    unavailable_reason: str | None = None
    input_refreshed_at: datetime | None = None


@dataclass(slots=True)
class FeatureSummary:
    """Combined feature calculation status for a symbol."""

    symbol: str
    as_of: date
    technical: TechnicalFeatures | None = None
    fundamental: FundamentalFeatures | None = None
    status: str = "UNKNOWN"
    unavailable_reason: str | None = None
