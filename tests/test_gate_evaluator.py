"""Tests für die MVP-Gate-Evaluierung."""

from src.preprocessing.gate_evaluator import GATE_FAIL, GATE_PASS, GATE_PENDING, GateEvaluator


def test_gate_evaluator_returns_fail_for_missing_symbol() -> None:
    """Trades ohne Symbol müssen durchfallen."""
    decision = GateEvaluator().evaluate({"symbol": "", "qty": 10, "price": 5})
    assert decision.status == GATE_FAIL


def test_gate_evaluator_returns_pending_for_missing_price() -> None:
    """Ohne gültigen Preis bleibt der Trade im Status PENDING."""
    decision = GateEvaluator().evaluate({"symbol": "AAPL", "qty": 10, "price": None})
    assert decision.status == GATE_PENDING


def test_gate_evaluator_returns_pass_for_valid_trade() -> None:
    """Vollständige Basisdaten müssen PASS liefern."""
    trade = {
        "symbol": "AAPL",
        "qty": 500,
        "price": 100,
        "transaction_type": "P-Purchase",
        "security_name": "Common Stock",
        "acquisition_or_disposition": "A",
    }
    decision = GateEvaluator().evaluate(trade)
    assert decision.status == GATE_PASS
