from __future__ import annotations

from src.services.scoring_service import ScoringService


def test_compute_trade_score_invalid_returns_zero_and_invalid() -> None:
    service = ScoringService()
    result = service.compute_trade_score(
        {
            "validation_status": "INVALID",
            "gate_status": "PASS",
            "transaction_type": "P-Purchase",
            "trade_value": 5_000_000,
            "acquisition_or_disposition": "A",
        }
    )
    assert result["score"] == 0
    assert result["final_score"] == 0
    assert result["score_class"] == "E"
    assert result["final_class"] == "E"
    assert result["decision_status"] == "INVALID"


def test_compute_trade_score_pre_gate_fail_returns_zero() -> None:
    service = ScoringService()
    result = service.compute_trade_score(
        {
            "validation_status": "VALID",
            "gate_status": "PRE_GATE_FAIL",
            "transaction_type": "P-Purchase",
            "trade_value": 5_000_000,
            "acquisition_or_disposition": "A",
        }
    )
    assert result["score"] == 0
    assert result["final_score"] == 0
    assert result["decision_status"] == "PRE_GATE_FAIL"


def test_compute_trade_score_pass_still_uses_buy_engine() -> None:
    service = ScoringService()
    result = service.compute_trade_score(
        {
            "validation_status": "VALID",
            "gate_status": "PASS",
            "transaction_type": "P-Purchase",
            "transaction_code_class": "CORE_BUY",
            "trade_value": 5_000_000,
            "market_cap": 10_000_000_000,
            "avg_20d_dollar_volume": 50_000_000,
            "acquisition_or_disposition": "A",
            "type_of_owner": "CEO",
            "technical_state": "STRONG",
            "earnings_distance_days": 30,
            "tr_availability_state": "CONFIRMED_MATCH",
            "tr_tradability_state": "GOOD",
            "normalized_instrument_type": "OPERATING_COMPANY_EQUITY",
        }
    )
    assert result["final_score"] > 0
    assert result["decision_status"] != "INVALID"
    assert result["decision_status"] != "PRE_GATE_FAIL"


def test_compute_trade_score_missing_gate_status_does_not_auto_fail() -> None:
    service = ScoringService()
    result = service.compute_trade_score(
        {
            "validation_status": "VALID",
            "transaction_type": "P-Purchase",
            "transaction_code_class": "CORE_BUY",
            "trade_value": 500_000,
            "acquisition_or_disposition": "A",
        }
    )
    assert result["decision_status"] != "PRE_GATE_FAIL"

