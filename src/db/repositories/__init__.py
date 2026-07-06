"""Repository package exports for legacy and planned stock-analysis modules."""

STOCK_ANALYSIS_REPOSITORY_MODULES = (
    "watchlist_repository",
    "stock_price_repository",
    "fundamental_metrics_repository",
    "feature_repository",
    "prediction_repository",
    "backtest_repository",
    "preference_score_repository",
    "import_run_repository",
    "data_quality_repository",
)

__all__ = ["STOCK_ANALYSIS_REPOSITORY_MODULES"]
