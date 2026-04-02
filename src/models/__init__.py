"""Projektmodelle für Trades, Firmen und Analyseergebnisse."""

from src.models.analysis_result import AnalysisResult
from src.models.company import Company
from src.models.insider_trade import InsiderTrade

__all__ = ["InsiderTrade", "Company", "AnalysisResult"]
