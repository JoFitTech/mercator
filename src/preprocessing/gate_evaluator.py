"""Lokale Gate-Prüfung für Insider-Trades im MVP."""

from __future__ import annotations

from dataclasses import dataclass

GATE_PENDING = "PENDING"
GATE_PASS = "PASS"
GATE_FAIL = "FAIL"


@dataclass(slots=True)
class GateDecision:
    """Ergebniscontainer für die lokale Gate-Entscheidung."""

    status: str
    reason: str | None = None


@dataclass(slots=True)
class GateRules:
    """Fachlich fixierte Regeln für die finale lokale Gate-Entscheidung."""

    min_trade_value: int = 100_000
    allowed_acquisition_or_disposition: tuple[str, ...] = ("A", "D")
    excluded_transaction_types: tuple[str, ...] = ("A-Award", "M-Exempt")
    required_form_type: str = "4"
    required_validation_status: str = "VALID"
    max_filing_age_days: int = 45


class GateEvaluator:
    """Bewertet Trades lokal mit konservativen MVP-Regeln."""

    def __init__(self, rules: GateRules | None = None) -> None:
        self.rules = rules or GateRules()

    def evaluate(self, trade: dict) -> GateDecision:
        """Prüft ein normalisiertes Trade-Dict mit einfachen Regeln.

        Parameter:
            trade: Normalisiertes Trade-Dictionary.

        Rückgabe:
            GateDecision mit Status und Begründung.
        """

        symbol = str(trade.get("symbol", "")).strip().upper()
        filing_date = trade.get("filing_date")
        transaction_date = trade.get("transaction_date")
        qty = trade.get("qty") or 0
        price = trade.get("price") or 0
        trade_value_raw = trade.get("trade_value_estimated")
        trade_value: float | None = None
        try:
            if trade_value_raw is not None:
                trade_value = float(trade_value_raw)  # type: ignore
        except (TypeError, ValueError):
            trade_value = None
        validation_status = str(trade.get("validation_status") or "VALID").upper()
        transaction_type = str(trade.get("transaction_type", "")).strip()
        acquisition = str(trade.get("acquisition_or_disposition", "")).upper()
        form_type = str(trade.get("form_type", "")).strip()
        is_actively_trading = trade.get("is_actively_trading")
        filing_age_days = trade.get("filing_age_days")

        if not symbol:
            return GateDecision(status=GATE_FAIL, reason="Fehlendes Symbol")
        if filing_date is None or transaction_date is None:
            return GateDecision(status=GATE_FAIL, reason="Datum nicht parsebar")
        if qty <= 0:
            return GateDecision(status=GATE_FAIL, reason="Ungültige Stückzahl")
        if validation_status != self.rules.required_validation_status.upper():
            return GateDecision(status=GATE_FAIL, reason="Validation-Status nicht zulässig")
        if validation_status == "PRICE_INVALID":
            return GateDecision(status=GATE_FAIL, reason="Preis fachlich ungültig")
        if price <= 0:
            return GateDecision(status=GATE_FAIL, reason="Preis fehlt oder ist ungültig")

        allowed = {value.upper() for value in self.rules.allowed_acquisition_or_disposition}
        if acquisition not in allowed:
            return GateDecision(status=GATE_FAIL, reason="Acquisition/Disposition nicht erlaubt")

        if form_type != self.rules.required_form_type:
            return GateDecision(status=GATE_FAIL, reason="Form Type nicht zulässig")

        excluded_transaction_types = {value.casefold() for value in self.rules.excluded_transaction_types}
        if transaction_type.casefold() in excluded_transaction_types:
            return GateDecision(status=GATE_FAIL, reason="Transaktionstyp ausgeschlossen")

        if trade_value is None or trade_value < self.rules.min_trade_value:
            return GateDecision(status=GATE_FAIL, reason="Transaktionswert unter Mindestschwelle")
        if is_actively_trading is False:
            return GateDecision(status=GATE_FAIL, reason="Instrument nicht aktiv handelbar")
        if filing_age_days is not None:
            try:
                if int(filing_age_days) > self.rules.max_filing_age_days:
                    return GateDecision(status=GATE_FAIL, reason="Filing zu alt")
            except (TypeError, ValueError):
                return GateDecision(status=GATE_FAIL, reason="Filing-Alter ungültig")

        return GateDecision(status=GATE_PASS, reason="Basisregeln erfüllt")
