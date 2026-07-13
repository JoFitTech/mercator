from __future__ import annotations

from src.services.stock_analysis_service import StockAnalysisService


class _Repo:
    def __init__(self, **methods):
        self.__dict__.update(methods)


def test_stock_detail_aggregates_partial_data_with_explicit_statuses() -> None:
    service = StockAnalysisService(
        watchlist_repository=None,
        data_quality_repository=_Repo(
            list_issues=lambda **_kwargs: [
                {
                    "data_category": "prediction",
                    "severity": "ERROR",
                    "status": "OPEN",
                    "message": "Prediction refresh failed.",
                    "source_refreshed_at": "2026-07-09T12:00:00Z",
                }
            ]
        ),
        company_repository=_Repo(
            resolve_symbol=lambda _symbol: {"current_symbol": "AAPL", "company_name": "Apple Inc."},
            get_stock_profile_status=lambda _symbol: {
                "profile_status": "READY",
                "profile_updated_at": "2026-07-10T12:00:00Z",
            },
        ),
        price_repository=_Repo(
            list_prices=lambda _symbol, limit=250: [
                {
                    "price_date": "2026-07-10",
                    "close_price": 212.25,
                    "quality_status": "STALE",
                    "source_refreshed_at": "2026-07-10T22:00:00Z",
                }
            ]
        ),
        technical_feature_repository=_Repo(get_latest=lambda _symbol: None),
        fundamental_feature_repository=_Repo(
            get_latest=lambda _symbol: {"feature_status": "INCOMPLETE", "unavailable_reason": "Missing valuation."}
        ),
        prediction_repository=_Repo(list_predictions=lambda symbol=None, limit=20: []),
        preference_repository=_Repo(get_latest=lambda _symbol: None),
    )

    detail = service.get_stock_detail("aapl")

    assert detail["symbol"] == "AAPL"
    assert detail["profile"]["company_name"] == "Apple Inc."
    assert detail["statuses"]["profile"]["status"] == "READY"
    assert detail["statuses"]["prices"]["status"] == "STALE"
    assert detail["statuses"]["technical_features"]["status"] == "MISSING"
    assert detail["statuses"]["fundamental_features"]["status"] == "INCOMPLETE"
    assert detail["statuses"]["predictions"]["status"] == "FAILED"
    assert "Prediction refresh failed" in detail["statuses"]["predictions"]["message"]
    assert detail["statuses"]["preference"]["status"] == "MISSING"


def test_stock_detail_rejects_empty_symbol() -> None:
    service = StockAnalysisService(None, None)

    try:
        service.get_stock_detail("  ")
    except ValueError as exc:
        assert "symbol" in str(exc).lower()
    else:
        raise AssertionError("Expected an empty symbol to be rejected.")
