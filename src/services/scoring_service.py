"""Zentraler Scoring-Service für Mercator."""

from __future__ import annotations
from typing import Any
import pandas as pd
from src.domain_rules import classify_score, ScoreGatePolicy
from src.services.buy_engine import score_trade

class ScoringService:
    """Zentrale Instanz für alle Score-Berechnungen und Klassifizierungen."""

    def __init__(self, policy: ScoreGatePolicy | None = None) -> None:
        self.policy = policy or ScoreGatePolicy()

    def compute_trade_score(self, trade: dict[str, Any] | pd.Series) -> dict[str, Any]:
        """Berechnet Score und Klasse für einen einzelnen Trade."""
        # Konvertierung von pd.Series falls nötig
        trade_dict = trade.to_dict() if isinstance(trade, pd.Series) else trade
        
        result = score_trade(trade_dict)
        score = result.final_score
        score_class = result.final_class
        
        # Zusätzlich das Label (PASS/HOLD/FAIL) und die Farbe basierend auf der Policy
        status_label, status_color = classify_score(score, self.policy)
        
        return {
            "score": score,
            "score_class": score_class,
            "status_label": status_label,
            "status_color": status_color,
            "core_insider_score": result.core_insider_score,
            "investability_score": result.investability_score,
            "execution_score": result.execution_score,
            "trade_republic_score": result.trade_republic_score,
            "final_score": result.final_score,
            "final_class": result.final_class,
            "decision_status": result.decision_status,
            "filing_age_days": result.filing_age_days,
        }

    def compute_insider_quality(self, reporting_name: str, trades_df: pd.DataFrame) -> dict[str, Any]:
        """Hilfslogik zur Bewertung der Qualität eines Insiders basierend auf seinen Trades."""
        # Diese Logik war teilweise in AnalysisService angedeutet oder vorbereitet
        if trades_df.empty:
            return {"score": 0, "label": "No Data"}
            
        insider_trades = trades_df[trades_df["reporting_name"] == reporting_name]
        if insider_trades.empty:
            return {"score": 0, "label": "No Data"}
            
        avg_score = insider_trades["score"].mean()
        
        if avg_score >= 80: label = "High Precision"
        elif avg_score >= 50: label = "Reliable"
        else: label = "Occasional"
        
        return {
            "average_score": avg_score,
            "trade_count": len(insider_trades),
            "quality_label": label
        }
