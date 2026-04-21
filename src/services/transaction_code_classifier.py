"""Normative Transaction-Code-Taxonomie (FMP API Spec v2 Final)."""

from __future__ import annotations

from dataclasses import dataclass

CORE_BUY = "CORE_BUY"
CORE_SELL = "CORE_SELL"
SECONDARY_SIGNAL = "SECONDARY_SIGNAL"
MANUAL_REVIEW = "MANUAL_REVIEW"
EXCLUDE_FROM_CORE = "EXCLUDE_FROM_CORE"


@dataclass(frozen=True, slots=True)
class TransactionCodeInfo:
    code: str
    classification: str
    explanation: str


class TransactionCodeClassifier:
    """Classifies raw transaction codes into normative operational classes."""

    _MATRIX: dict[str, TransactionCodeInfo] = {
        "P": TransactionCodeInfo("P", CORE_BUY, "Purchase: strongest positive buy signal."),
        "S": TransactionCodeInfo("S", CORE_SELL, "Sale: strongest negative sell signal."),
        "I": TransactionCodeInfo("I", SECONDARY_SIGNAL, "Discretionary transaction, weaker than P."),
        "L": TransactionCodeInfo("L", SECONDARY_SIGNAL, "Small acquisition/disposition hint, never core buy."),
        "J": TransactionCodeInfo("J", MANUAL_REVIEW, "Other transaction; requires context."),
        "V": TransactionCodeInfo("V", MANUAL_REVIEW, "Voluntary marker; requires context."),
    }

    _EXCLUDED_CODES = {
        "A", "C", "D", "E", "F", "G", "H", "M", "O", "U", "W", "X", "Z", "K",
    }

    @classmethod
    def classify(cls, transaction_type: str | None) -> TransactionCodeInfo:
        raw = str(transaction_type or "").strip().upper()
        # Supports values like "P-Purchase" from FMP payloads.
        code = raw[:1] if raw else ""
        if code in cls._MATRIX:
            return cls._MATRIX[code]
        if code in cls._EXCLUDED_CODES:
            return TransactionCodeInfo(code=code, classification=EXCLUDE_FROM_CORE, explanation="Non-core technical/ownership event.")
        return TransactionCodeInfo(code=code or "UNKNOWN", classification=MANUAL_REVIEW, explanation="Unknown code; requires manual review.")
