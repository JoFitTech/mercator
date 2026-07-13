"""Feature Engineering fuer Watchlist-Symbole."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from src.db.repositories.data_quality_repository import DataQualityRepository
from src.db.repositories.feature_repository import FundamentalFeatureRepository, TechnicalFeatureRepository
from src.db.repositories.fundamental_metrics_repository import FundamentalMetricsRepository
from src.db.repositories.stock_price_repository import StockPriceRepository
from src.db.repositories.watchlist_repository import WatchlistRepository
from src.models.features import FeatureSummary, FundamentalFeatures, TechnicalFeatures
from src.models.watchlist import DataQualityIssue
from src.services.historical_market_data_service import HistoricalMarketDataService


class FeatureEngineeringService:
    """Berechnet und persistiert technische und fundamentale Stock-Features."""

    COMPLETE_FUNDAMENTAL_FIELDS = (
        "revenue_growth",
        "gross_margin",
        "valuation_ratio",
        "debt_to_equity",
        "market_cap",
    )

    def __init__(
        self,
        price_repository: StockPriceRepository,
        metrics_repository: FundamentalMetricsRepository,
        technical_feature_repository: TechnicalFeatureRepository,
        fundamental_feature_repository: FundamentalFeatureRepository,
        watchlist_repository: WatchlistRepository | None = None,
        data_quality_repository: DataQualityRepository | None = None,
    ) -> None:
        self.price_repository = price_repository
        self.metrics_repository = metrics_repository
        self.technical_feature_repository = technical_feature_repository
        self.fundamental_feature_repository = fundamental_feature_repository
        self.watchlist_repository = watchlist_repository
        self.data_quality_repository = data_quality_repository

    @staticmethod
    def _symbol(value: str) -> str:
        return str(value or "").strip().upper()

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _metric_key(value: Any) -> str:
        return str(value or "").strip().lower()

    def calculate_for_symbol(self, symbol: str) -> FeatureSummary:
        normalized_symbol = self._symbol(symbol)
        if not normalized_symbol:
            raise ValueError("Feature calculation requires a symbol.")

        technical = self._calculate_technical_features(normalized_symbol)
        fundamental = self._calculate_fundamental_features(normalized_symbol, technical.feature_date)

        self.technical_feature_repository.upsert_feature(technical)
        self.fundamental_feature_repository.upsert_feature(fundamental)
        self._record_quality_issue(technical.symbol, "technical_features", technical.feature_status, technical.unavailable_reason)
        self._record_quality_issue(
            fundamental.symbol,
            "fundamental_features",
            fundamental.feature_status,
            fundamental.unavailable_reason,
        )

        status = self._combined_status(technical.feature_status, fundamental.feature_status)
        reasons = [reason for reason in (technical.unavailable_reason, fundamental.unavailable_reason) if reason]
        return FeatureSummary(
            symbol=normalized_symbol,
            as_of=technical.feature_date,
            technical=technical,
            fundamental=fundamental,
            status=status,
            unavailable_reason=" | ".join(reasons) or None,
        )

    def calculate_for_watchlist(self, active_only: bool = True) -> list[FeatureSummary]:
        if self.watchlist_repository is None:
            return []
        summaries: list[FeatureSummary] = []
        for item in self.watchlist_repository.list_items(active_only=active_only):
            symbol = self._symbol(str(item.get("symbol") or ""))
            if symbol:
                summaries.append(self.calculate_for_symbol(symbol))
        return summaries

    def _calculate_technical_features(self, symbol: str) -> TechnicalFeatures:
        rows = self.price_repository.list_prices(symbol, limit=500)
        payload = HistoricalMarketDataService.calculate_price_features(rows)
        feature_date = payload.pop("feature_date", None) or date.today()
        return TechnicalFeatures(symbol=symbol, feature_date=feature_date, **payload)

    def _calculate_fundamental_features(self, symbol: str, fallback_period: date) -> FundamentalFeatures:
        rows = self.metrics_repository.list_metrics(symbol, limit=500)
        if not rows:
            return FundamentalFeatures(
                symbol=symbol,
                feature_period=fallback_period,
                feature_status="MISSING",
                unavailable_reason="No fundamental metrics available.",
            )

        latest_by_name = self._latest_metrics_by_name(rows)
        latest_period = max((row.get("period_end") for row in rows if isinstance(row.get("period_end"), date)), default=fallback_period)
        payload: dict[str, Any] = {
            "symbol": symbol,
            "feature_period": latest_period,
            "revenue_growth": self._metric_value(latest_by_name, "revenue_growth"),
            "earnings_growth": self._metric_value(latest_by_name, "earnings_growth"),
            "gross_margin": self._metric_value(latest_by_name, "gross_margin"),
            "operating_margin": self._metric_value(latest_by_name, "operating_margin"),
            "net_margin": self._metric_value(latest_by_name, "net_margin"),
            "valuation_ratio": self._metric_value(latest_by_name, "valuation_ratio", "pe_ratio"),
            "debt_to_equity": self._metric_value(latest_by_name, "debt_to_equity"),
            "market_cap": self._to_int(self._metric_value(latest_by_name, "market_cap")),
            "input_refreshed_at": self._latest_refreshed_at(rows),
        }
        missing = [field for field in self.COMPLETE_FUNDAMENTAL_FIELDS if payload.get(field) is None]
        payload["feature_status"] = "READY" if not missing else "INCOMPLETE"
        payload["unavailable_reason"] = None if not missing else f"Missing fundamental fields: {', '.join(missing)}."
        return FundamentalFeatures(**payload)

    def _latest_metrics_by_name(self, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        ordered = sorted(rows, key=lambda row: str(row.get("period_end") or ""), reverse=True)
        latest: dict[str, dict[str, Any]] = {}
        for row in ordered:
            latest.setdefault(self._metric_key(row.get("metric_name")), row)
        return latest

    def _metric_value(self, latest_by_name: dict[str, dict[str, Any]], *names: str) -> float | None:
        for name in names:
            row = latest_by_name.get(self._metric_key(name))
            if row is not None:
                return self._to_float(row.get("value"))
        return None

    @staticmethod
    def _latest_refreshed_at(rows: list[dict[str, Any]]) -> datetime | None:
        values = [row.get("source_refreshed_at") for row in rows if isinstance(row.get("source_refreshed_at"), datetime)]
        return max(values) if values else None

    @staticmethod
    def _combined_status(technical_status: str, fundamental_status: str) -> str:
        statuses = {technical_status.upper(), fundamental_status.upper()}
        if statuses == {"READY"}:
            return "READY"
        if "MISSING" in statuses:
            return "MISSING"
        return "INCOMPLETE"

    def _record_quality_issue(self, symbol: str, category: str, status: str, reason: str | None) -> None:
        if self.data_quality_repository is None or status.upper() == "READY":
            return
        self.data_quality_repository.create_issue(
            DataQualityIssue(
                symbol=symbol,
                data_category=category,
                severity="WARNING" if status.upper() == "INCOMPLETE" else "ERROR",
                status="OPEN",
                message=reason or f"{category} status is {status.upper()}.",
                detected_at=datetime.now(UTC),
            )
        )
