"""Zentraler Scoring-Service für Mercator."""

from __future__ import annotations
from typing import Any
import pandas as pd
from src.domain_rules import classify_score, ScoreGatePolicy
from src.services.buy_engine import score_trade

_FAIL_ZERO: dict[str, Any] = {
    "score": 0,
    "score_class": "E",
    "status_label": "FAIL",
    "status_color": "#ef4444",
    "core_insider_score": 0,
    "investability_score": 0,
    "execution_score": 0,
    "trade_republic_score": 0,
    "final_score": 0,
    "final_class": "E",
}


class ScoringService:
    """Zentrale Instanz für alle Score-Berechnungen und Klassifizierungen."""

    def __init__(self, policy: ScoreGatePolicy | None = None) -> None:
        self.policy = policy or ScoreGatePolicy()

    def compute_trade_score(self, trade: dict[str, Any] | pd.Series) -> dict[str, Any]:
        """Berechnet Score und Klasse für einen einzelnen Trade.

        INVALID- und PRE_GATE_FAIL-Trades werden früh zurückgegeben mit Score 0
        und können nie BUY_CANDIDATE oder ACTIONABLE_BUY werden.
        """
        # Konvertierung von pd.Series falls nötig
        trade_dict = trade.to_dict() if isinstance(trade, pd.Series) else trade

        validation_status = str(trade_dict.get("validation_status") or "").upper()
        gate_status = str(trade_dict.get("gate_status") or "").upper()

        if validation_status and validation_status not in {"VALID", ""}:
            return {
                **_FAIL_ZERO,
                "decision_status": "INVALID",
                "filing_age_days": trade_dict.get("filing_age_days"),
            }

        if gate_status and gate_status not in {"PASS", "PENDING"}:
            return {
                **_FAIL_ZERO,
                "decision_status": "PRE_GATE_FAIL",
                "filing_age_days": trade_dict.get("filing_age_days"),
            }

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
