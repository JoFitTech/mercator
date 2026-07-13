"""Read-only Stock-Analysis-Querien fuer Watchlist und Status-Text."""

from __future__ import annotations

from typing import Any

from src.db.repositories.data_quality_repository import DataQualityRepository
from src.db.repositories.watchlist_repository import WatchlistRepository
from src.preprocessing.data_quality_evaluator import (
    QUALITY_FAILED,
    QUALITY_INCOMPLETE,
    QUALITY_MISSING,
    QUALITY_READY,
    build_data_quality_message,
    normalize_data_quality_status,
)


class StockAnalysisService:
    """Sammelt Watchlist-Status und sichtbare Datenqualitaets-Strings."""

    def __init__(
        self,
        watchlist_repository: WatchlistRepository | None,
        data_quality_repository: DataQualityRepository | None,
        *,
        company_repository: Any | None = None,
        price_repository: Any | None = None,
        technical_feature_repository: Any | None = None,
        fundamental_feature_repository: Any | None = None,
        prediction_repository: Any | None = None,
        preference_repository: Any | None = None,
    ) -> None:
        self.watchlist_repository = watchlist_repository
        self.data_quality_repository = data_quality_repository
        self.company_repository = company_repository
        self.price_repository = price_repository
        self.technical_feature_repository = technical_feature_repository
        self.fundamental_feature_repository = fundamental_feature_repository
        self.prediction_repository = prediction_repository
        self.preference_repository = preference_repository

    def list_watchlist_items_with_status(self, active_only: bool = False) -> list[dict[str, Any]]:
        if self.watchlist_repository is None:
            return []

        items = self.watchlist_repository.list_items(active_only=active_only)
        enriched: list[dict[str, Any]] = []
        for item in items:
            symbol = str(item.get("symbol") or "").strip().upper()
            data_quality_summary = "Keine offenen Datenqualitaetsprobleme."
            if self.data_quality_repository is not None:
                unresolved_issues = self.data_quality_repository.list_issues(symbol=symbol, unresolved_only=True, limit=1000)
                if unresolved_issues:
                    data_quality_summary = f"{len(unresolved_issues)} offene Datenqualitaetsprobleme."

            enriched_item = dict(item)
            enriched_item["profile_status_text"] = build_data_quality_message(
                QUALITY_MISSING,
                data_category="company_profile",
                reason="Noch nicht importiert",
            )
            enriched_item["price_status_text"] = build_data_quality_message(
                QUALITY_MISSING,
                data_category="historical_price",
                reason="Noch nicht importiert",
            )
            enriched_item["financial_status_text"] = build_data_quality_message(
                QUALITY_MISSING,
                data_category="financial_metrics",
                reason="Noch nicht importiert",
            )
            enriched_item["prediction_status_text"] = build_data_quality_message(
                QUALITY_MISSING,
                data_category="prediction",
                reason="Noch nicht berechnet",
            )
            enriched_item["preference_status_text"] = build_data_quality_message(
                QUALITY_MISSING,
                data_category="preference_score",
                reason="Noch nicht berechnet",
            )
            enriched_item["data_quality_summary"] = data_quality_summary
            enriched.append(enriched_item)
        return enriched

    def build_watchlist_summary(self, active_only: bool = False) -> dict[str, Any]:
        items = self.watchlist_repository.list_items(active_only=active_only) if self.watchlist_repository else []
        unresolved_count = sum(
            1 for item in items if str(item.get("resolution_status") or "").strip().upper() != "RESOLVED"
        )
        resolved_count = len(items) - unresolved_count
        unresolved_text = build_data_quality_message(
            QUALITY_MISSING,
            data_category="watchlist",
            reason="Eintraege benoetigen eine Datenanbindung",
        )
        return {
            "total_items": len(items),
            "active_items": sum(1 for item in items if bool(item.get("active", True))),
            "resolved_items": resolved_count,
            "unresolved_items": unresolved_count,
            "unresolved_text": unresolved_text,
        }

    @staticmethod
    def _status_payload(
        status: Any,
        *,
        category: str,
        reason: Any | None = None,
        refreshed_at: Any | None = None,
        message: str | None = None,
    ) -> dict[str, Any]:
        canonical = normalize_data_quality_status(status)
        return {
            "status": canonical,
            "message": message
            or build_data_quality_message(
                canonical,
                data_category=category,
                reason=reason,
                source_refreshed_at=refreshed_at if hasattr(refreshed_at, "isoformat") else None,
            ),
            "source_refreshed_at": refreshed_at,
        }

    @staticmethod
    def _issue_quality_status(issue: dict[str, Any]) -> str:
        severity = str(issue.get("severity") or "").strip().upper()
        if severity in {"ERROR", "CRITICAL", "FAILED", "FAIL"}:
            return QUALITY_FAILED
        return QUALITY_INCOMPLETE

    @staticmethod
    def _issue_for_category(issues: list[dict[str, Any]], *categories: str) -> dict[str, Any] | None:
        wanted = {category.lower() for category in categories}
        return next(
            (
                issue
                for issue in issues
                if str(issue.get("data_category") or "").strip().lower() in wanted
            ),
            None,
        )

    @staticmethod
    def _safe_read(callback, fallback):  # noqa: ANN001, ANN202 - repository adapter boundary
        try:
            return callback(), None
        except Exception as exc:  # noqa: BLE001 - one failed dataset must not hide the detail page
            return fallback, exc

    def get_stock_detail(self, symbol: str) -> dict[str, Any]:
        """Return a fault-isolated read model for the complete stock detail page."""

        normalized_symbol = str(symbol or "").strip().upper()
        if not normalized_symbol:
            raise ValueError("A stock symbol is required.")

        issues, issues_error = self._safe_read(
            lambda: self.data_quality_repository.list_issues(
                symbol=normalized_symbol,
                unresolved_only=True,
                limit=100,
            )
            if self.data_quality_repository is not None
            else [],
            [],
        )
        profile, profile_error = self._safe_read(
            lambda: self.company_repository.resolve_symbol(normalized_symbol)
            if self.company_repository is not None
            else None,
            None,
        )
        profile_status, profile_status_error = self._safe_read(
            lambda: self.company_repository.get_stock_profile_status(normalized_symbol)
            if self.company_repository is not None
            else None,
            None,
        )
        prices, prices_error = self._safe_read(
            lambda: self.price_repository.list_prices(normalized_symbol, limit=250)
            if self.price_repository is not None
            else [],
            [],
        )
        technical, technical_error = self._safe_read(
            lambda: self.technical_feature_repository.get_latest(normalized_symbol)
            if self.technical_feature_repository is not None
            else None,
            None,
        )
        fundamental, fundamental_error = self._safe_read(
            lambda: self.fundamental_feature_repository.get_latest(normalized_symbol)
            if self.fundamental_feature_repository is not None
            else None,
            None,
        )
        predictions, predictions_error = self._safe_read(
            lambda: self.prediction_repository.list_predictions(symbol=normalized_symbol, limit=20)
            if self.prediction_repository is not None
            else [],
            [],
        )
        preference, preference_error = self._safe_read(
            lambda: self.preference_repository.get_latest(normalized_symbol)
            if self.preference_repository is not None
            else None,
            None,
        )

        profile_record = profile_status or profile or {}
        latest_price = prices[0] if prices else {}
        latest_prediction = predictions[0] if predictions else {}
        statuses = {
            "profile": self._status_payload(
                QUALITY_FAILED
                if profile_error or profile_status_error
                else (profile_record.get("profile_status") or (QUALITY_READY if profile else QUALITY_MISSING)),
                category="company_profile",
                reason=str(profile_error or profile_status_error) if profile_error or profile_status_error else profile_record.get("profile_reason"),
                refreshed_at=profile_record.get("profile_updated_at"),
            ),
            "prices": self._status_payload(
                QUALITY_FAILED
                if prices_error
                else (latest_price.get("quality_status") or (QUALITY_READY if prices else QUALITY_MISSING)),
                category="historical_price",
                reason=str(prices_error) if prices_error else None,
                refreshed_at=latest_price.get("source_refreshed_at"),
            ),
            "technical_features": self._status_payload(
                QUALITY_FAILED
                if technical_error
                else ((technical or {}).get("feature_status") or (QUALITY_READY if technical else QUALITY_MISSING)),
                category="technical_features",
                reason=str(technical_error) if technical_error else (technical or {}).get("unavailable_reason"),
                refreshed_at=(technical or {}).get("input_refreshed_at"),
            ),
            "fundamental_features": self._status_payload(
                QUALITY_FAILED
                if fundamental_error
                else ((fundamental or {}).get("feature_status") or (QUALITY_READY if fundamental else QUALITY_MISSING)),
                category="fundamental_features",
                reason=str(fundamental_error) if fundamental_error else (fundamental or {}).get("unavailable_reason"),
                refreshed_at=(fundamental or {}).get("input_refreshed_at"),
            ),
            "predictions": self._status_payload(
                QUALITY_FAILED if predictions_error else QUALITY_READY if predictions else QUALITY_MISSING,
                category="prediction",
                reason=str(predictions_error) if predictions_error else None,
                refreshed_at=latest_prediction.get("input_refreshed_at"),
            ),
            "preference": self._status_payload(
                QUALITY_FAILED if preference_error else QUALITY_READY if preference else QUALITY_MISSING,
                category="preference_score",
                reason=str(preference_error) if preference_error else (preference or {}).get("data_quality_summary"),
                refreshed_at=(preference or {}).get("score_as_of"),
            ),
        }

        issue_categories = {
            "profile": ("company_profile",),
            "prices": ("historical_price",),
            "technical_features": ("feature", "technical_features"),
            "fundamental_features": ("financial_metric", "financial_metrics", "fundamental_features"),
            "predictions": ("prediction", "model_run"),
            "preference": ("preference_score",),
        }
        for key, categories in issue_categories.items():
            issue = self._issue_for_category(issues, *categories)
            if issue is not None:
                statuses[key] = self._status_payload(
                    self._issue_quality_status(issue),
                    category=categories[0],
                    refreshed_at=issue.get("source_refreshed_at"),
                    message=str(issue.get("message") or "Datenqualitaetsproblem ohne Detailtext."),
                )

        return {
            "symbol": normalized_symbol,
            "profile": profile,
            "prices": prices,
            "technical_features": technical,
            "fundamental_features": fundamental,
            "predictions": predictions,
            "preference_score": preference,
            "quality_issues": issues,
            "statuses": statuses,
            "quality_read_error": str(issues_error) if issues_error else None,
        }
