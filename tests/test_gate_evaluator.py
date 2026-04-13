"""Tests für die finale Pre-Gate-Evaluierung."""

from src.preprocessing.gate_evaluator import (
    GATE_FAIL,
    GATE_PASS,
    GateEvaluator,
)


def _valid_trade() -> dict:
    return {
        "symbol": "AAPL",
        "filing_date": "2026-04-01",
        "transaction_date": "2026-04-01",
        "qty": 1000,
        "price": 120,
        "trade_value_estimated": 120000,
        "transaction_type": "P-Purchase",
        "security_name": "Common Stock",
        "acquisition_or_disposition": "A",
        "form_type": "4",
        "validation_status": "VALID",
    }


def test_gate_evaluator_returns_fail_for_missing_symbol() -> None:
    decision = GateEvaluator().evaluate({**_valid_trade(), "symbol": ""})
    assert decision.status == GATE_FAIL


def test_gate_evaluator_returns_fail_for_missing_price() -> None:
    decision = GateEvaluator().evaluate({**_valid_trade(), "price": None})
    assert decision.status == GATE_FAIL


def test_gate_evaluator_returns_fail_for_price_invalid_status() -> None:
    decision = GateEvaluator().evaluate({**_valid_trade(), "validation_status": "PRICE_INVALID"})
    assert decision.status == GATE_FAIL


def test_gate_evaluator_returns_fail_for_excluded_transaction_type() -> None:
    decision = GateEvaluator().evaluate({**_valid_trade(), "transaction_type": "A-Award"})
    assert decision.status == GATE_FAIL


def test_gate_evaluator_returns_fail_for_low_trade_value() -> None:
    decision = GateEvaluator().evaluate({**_valid_trade(), "trade_value_estimated": 99999})
    assert decision.status == GATE_FAIL


def test_gate_evaluator_returns_pass_for_valid_trade() -> None:
    decision = GateEvaluator().evaluate(_valid_trade())
    assert decision.status == GATE_PASS

