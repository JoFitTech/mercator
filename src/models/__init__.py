"""Projektmodelle für Trades, Firmen und Analyseergebnisse."""

from src.models.analysis_result import AnalysisResult
from src.models.company import Company
from src.models.insider_trade import InsiderTrade

STOCK_ANALYSIS_MODEL_MODULES = (
    "stock",
    "watchlist",
    "features",
    "prediction",
    "preference",
)

__all__ = [
    "InsiderTrade",
    "Company",
    "AnalysisResult",
    "STOCK_ANALYSIS_MODEL_MODULES",
]
