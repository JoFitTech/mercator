"""Lokale Validation- und Pre-Gate-Logik für FMP API Specification v2 Final."""

from __future__ import annotations

from dataclasses import dataclass

from src.services.security_normalization_service import SecurityNormalizationService
from src.services.transaction_code_classifier import EXCLUDE_FROM_CORE, TransactionCodeClassifier

GATE_PENDING = "PENDING"
GATE_PASS = "PASS"
GATE_FAIL = "PRE_GATE_FAIL"


@dataclass(slots=True)
class GateDecision:
    status: str
    reason: str | None = None


@dataclass(slots=True)
class GateRules:
    min_trade_value: int = 100_000
    required_form_type: str = "4"
    max_filing_age_days_reject: int = 45
    filing_age_watchlist_days: int = 21
    allowed_acquisition_or_disposition: tuple[str, ...] = ("A", "D")
    excluded_transaction_types: tuple[str, ...] = ("A-Award", "M-Exempt")
    required_validation_status: str = "VALID"


class GateEvaluator:
    def __init__(self, rules: GateRules | None = None) -> None:
        self.rules = rules or GateRules()

    def evaluate(self, trade: dict) -> GateDecision:
        symbol = str(trade.get("symbol") or "").strip().upper()
        filing_date = trade.get("filing_date")
        transaction_date = trade.get("transaction_date")
        qty = float(trade.get("qty") or 0)
        price = float(trade.get("price") or 0)
        form_type = str(trade.get("form_type") or "").strip()
        validation_status = str(trade.get("validation_status") or "VALID").upper()
        transaction_type_raw = str(trade.get("transaction_type") or "").strip()
        transaction_type = transaction_type_raw.upper()
        transaction_code = transaction_type[:1]
        tx_class = str(
            trade.get("transaction_code_class")
            or TransactionCodeClassifier.classify(transaction_type_raw).classification
        ).upper()
        trade["transaction_code_class"] = tx_class
        is_actively_trading = trade.get("is_actively_trading")
        trade_value = float(trade.get("trade_value") or trade.get("trade_value_estimated") or 0)
        filing_age_days = trade.get("filing_age_days")
        instrument = str(
            trade.get("normalized_instrument_type")
            or SecurityNormalizationService.normalize(trade.get("security_name"))
        ).upper()

        # Validation Gate
        if not symbol:
            trade["validation_status"] = "INVALID"
            return GateDecision(status=GATE_FAIL, reason="missing_symbol")
        if filing_date is None or transaction_date is None:
            trade["validation_status"] = "INVALID"
            return GateDecision(status=GATE_FAIL, reason="missing_dates")
        if qty <= 0:
            trade["validation_status"] = "INVALID"
            return GateDecision(status=GATE_FAIL, reason="invalid_quantity")
        if price <= 0:
            trade["validation_status"] = "INVALID"
            return GateDecision(status=GATE_FAIL, reason="invalid_price")
        if validation_status in {"PRICE_INVALID", "INVALID"}:
            trade["validation_status"] = "INVALID"
            return GateDecision(status=GATE_FAIL, reason="invalid_validation_status")

        trade["validation_status"] = "VALID"

        # Filing Integrity Gate
        if form_type != self.rules.required_form_type:
            return GateDecision(status=GATE_FAIL, reason="form_type_not_4")

        excluded_types = {value.strip().upper() for value in self.rules.excluded_transaction_types}
        excluded_codes = {value.split("-", 1)[0] for value in excluded_types if value}
        if transaction_type in excluded_types or transaction_code in excluded_codes:
            return GateDecision(status=GATE_FAIL, reason="excluded_transaction_type")

        if tx_class == EXCLUDE_FROM_CORE:
            return GateDecision(status=GATE_FAIL, reason="excluded_transaction_code_class")

        aod = str(trade.get("acquisition_or_disposition") or "").strip().upper()
        if aod not in {value.upper() for value in self.rules.allowed_acquisition_or_disposition}:
            return GateDecision(status=GATE_FAIL, reason="acquisition_or_disposition_not_allowed")

        # Minimum Signal Size Gate
        if trade_value < self.rules.min_trade_value:
            return GateDecision(status=GATE_FAIL, reason="trade_value_below_threshold")

        # Instrument Gate
        if not SecurityNormalizationService.is_allowed(instrument):
            return GateDecision(status=GATE_FAIL, reason=f"instrument_not_allowed:{instrument}")

        if is_actively_trading is False:
            return GateDecision(status=GATE_FAIL, reason="instrument_not_actively_trading")

        # Filing Freshness
        try:
            filing_age = int(filing_age_days) if filing_age_days is not None else None
        except (TypeError, ValueError):
            return GateDecision(status=GATE_FAIL, reason="invalid_filing_age")
        if filing_age is not None and filing_age > self.rules.max_filing_age_days_reject:
            return GateDecision(status=GATE_FAIL, reason="filing_too_old")

        if filing_age is not None and filing_age > self.rules.filing_age_watchlist_days:
            return GateDecision(status=GATE_PENDING, reason="filing_watchlist")

        return GateDecision(status=GATE_PASS, reason="pass")
