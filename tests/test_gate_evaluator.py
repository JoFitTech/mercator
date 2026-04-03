"""Tests für die MVP-Gate-Evaluierung."""

from src.preprocessing.gate_evaluator import (
    GATE_FAIL,
    GATE_PASS,
    GATE_PENDING,
    GateEvaluator,
    GateRules,
)


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


def test_gate_evaluator_uses_configured_min_trade_value() -> None:
    """Ein konfigurierter Mindestwert soll auf die Entscheidung wirken."""

    trade = {
        "symbol": "AAPL",
        "qty": 200,
        "price": 100,
        "transaction_type": "P-Purchase",
        "security_name": "Common Stock",
        "acquisition_or_disposition": "A",
    }
    decision = GateEvaluator(GateRules(min_trade_value=25_000)).evaluate(trade)
    assert decision.status == GATE_FAIL


def test_gate_evaluator_can_disable_common_stock_rule() -> None:
    """Wenn deaktiviert, darf die Common-Stock-Pruefung keinen FAIL erzeugen."""

    trade = {
        "symbol": "AAPL",
        "qty": 500,
        "price": 100,
        "transaction_type": "P-Purchase",
        "security_name": "Preferred Stock",
        "acquisition_or_disposition": "A",
    }
    decision = GateEvaluator(GateRules(require_common_stock=False)).evaluate(trade)
    assert decision.status == GATE_PASS

