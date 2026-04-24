"""Tests fuer INVALID/PRE_GATE_FAIL-Guards in ScoringService."""

from __future__ import annotations

import pytest

from src.services.scoring_service import ScoringService


def _base_trade(**overrides) -> dict:
    trade = {
        "symbol": "AAPL",
        "validation_status": "VALID",
        "gate_status": "PASS",
        "transaction_type": "P-Purchase",
        "acquisition_or_disposition": "A",
        "trade_value": 500_000,
        "trade_value_estimated": 500_000,
        "filing_age_days": 3,
    }
    trade.update(overrides)
    return trade


def _is_zeroed(result: dict) -> bool:
    return (
        result["score"] == 0
        and result["score_class"] == "E"
        and result["final_score"] == 0
        and result["final_class"] == "E"
        and result["core_insider_score"] == 0
        and result["investability_score"] == 0
        and result["execution_score"] == 0
        and result["trade_republic_score"] == 0
    )


def test_invalid_validation_status_returns_zero_score() -> None:
    """validation_status=INVALID muss Score 0 und decision_status=INVALID liefern."""
    svc = ScoringService()
    result = svc.compute_trade_score(_base_trade(validation_status="INVALID"))

    assert _is_zeroed(result)
    assert result["decision_status"] == "INVALID"


def test_price_invalid_returns_zero_score() -> None:
    """validation_status=PRICE_INVALID muss Score 0 und decision_status=INVALID liefern."""
    svc = ScoringService()
    result = svc.compute_trade_score(_base_trade(validation_status="PRICE_INVALID"))

    assert _is_zeroed(result)
    assert result["decision_status"] == "INVALID"


def test_pre_gate_fail_gate_status_returns_zero_score() -> None:
    """gate_status=PRE_GATE_FAIL muss Score 0 und decision_status=PRE_GATE_FAIL liefern."""
    svc = ScoringService()
    result = svc.compute_trade_score(_base_trade(gate_status="PRE_GATE_FAIL"))

    assert _is_zeroed(result)
    assert result["decision_status"] == "PRE_GATE_FAIL"


def test_fail_gate_status_returns_zero_score() -> None:
    """gate_status=FAIL (generisch) muss Score 0 und decision_status=PRE_GATE_FAIL liefern."""
    svc = ScoringService()
    result = svc.compute_trade_score(_base_trade(gate_status="FAIL"))

    assert _is_zeroed(result)
    assert result["decision_status"] == "PRE_GATE_FAIL"


def test_valid_pass_trade_scores_normally() -> None:
    """Ein VALID+PASS Trade soll das normale Scoring durchlaufen (Score != INVALID/PRE_GATE_FAIL)."""
    svc = ScoringService()
    result = svc.compute_trade_score(_base_trade())

    assert result["decision_status"] not in {"INVALID", "PRE_GATE_FAIL"}


def test_no_gate_status_does_not_fail() -> None:
    """Fehlendes gate_status-Feld darf nicht automatisch zum Fail fuehren."""
    svc = ScoringService()
    trade = _base_trade()
    trade.pop("gate_status")
    result = svc.compute_trade_score(trade)

    assert result["decision_status"] not in {"INVALID", "PRE_GATE_FAIL"}


def test_invalid_preserves_filing_age_days() -> None:
    """filing_age_days soll bei INVALID-Trades unveraendert durchgereicht werden."""
    svc = ScoringService()
    result = svc.compute_trade_score(_base_trade(validation_status="INVALID", filing_age_days=7))

    assert result["filing_age_days"] == 7

