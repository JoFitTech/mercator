from __future__ import annotations

from src.services.dashboard_service import DashboardService


class _WatchlistRepo:
    def list_items(self, active_only: bool = False):  # noqa: ARG002
        return [
            {"symbol": "AAPL", "active": True, "resolution_status": "RESOLVED"},
            {"symbol": "MSFT", "active": True, "resolution_status": "UNRESOLVED"},
            {"symbol": "SAP", "active": False, "resolution_status": "RESOLVED"},
        ]


class _QualityRepo:
    def count_issues(self, unresolved_only: bool = False):  # noqa: ARG002
        return 4


def test_dashboard_stock_analysis_summary_uses_watchlist_and_quality_repositories() -> None:
    service = DashboardService(
        None,
        None,
        trade_repo=object(),
        company_repo=object(),
        watchlist_repo=_WatchlistRepo(),
        data_quality_repo=_QualityRepo(),
    )

    assert service._load_stock_analysis_summary() == {
        "watchlist_total": 3,
        "watchlist_active": 2,
        "watchlist_unresolved": 1,
        "open_data_quality_issues": 4,
    }
