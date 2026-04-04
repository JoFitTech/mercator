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
    """Konfigurierbare Regeln fuer die lokale Gate-Entscheidung."""

    min_trade_value: int = 10_000
    require_purchase_event: bool = True
    require_common_stock: bool = True
    allowed_acquisition_or_disposition: tuple[str, ...] = ("A",)
    allowed_transaction_types: tuple[str, ...] = ()


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
        qty = trade.get("qty") or 0
        price = trade.get("price") or 0
        transaction_type = str(trade.get("transaction_type", "")).lower()
        security_name = str(trade.get("security_name", "")).lower()
        acquisition = str(trade.get("acquisition_or_disposition", "")).upper()

        if not symbol:
            return GateDecision(status=GATE_FAIL, reason="Fehlendes Symbol")
        if qty <= 0:
            return GateDecision(status=GATE_FAIL, reason="Ungültige Stückzahl")
        if price <= 0:
            return GateDecision(status=GATE_PENDING, reason="Preis fehlt oder ist ungültig")

        # Offene Fachfragen sind zentral in ``docs/todos_offene_fragen.md`` dokumentiert.
        trade_value = qty * price
        if trade_value < self.rules.min_trade_value:
            return GateDecision(status=GATE_FAIL, reason="Transaktionswert unter Mindestschwelle")

        if self.rules.allowed_acquisition_or_disposition:
            allowed = {value.upper() for value in self.rules.allowed_acquisition_or_disposition}
            if acquisition and acquisition not in allowed:
                return GateDecision(status=GATE_FAIL, reason="Acquisition/Disposition nicht erlaubt")

        if self.rules.allowed_transaction_types:
            allowed_tx = {value.lower() for value in self.rules.allowed_transaction_types}
            if transaction_type.lower() not in allowed_tx:
                return GateDecision(status=GATE_FAIL, reason="Transaktionstyp nicht erlaubt")

        is_purchase = acquisition == "A" or "purchase" in transaction_type or "buy" in transaction_type
        if self.rules.require_purchase_event and not is_purchase:
            return GateDecision(status=GATE_FAIL, reason="Kein Kaufereignis")

        if self.rules.require_common_stock and security_name and "common stock" not in security_name:
            return GateDecision(status=GATE_FAIL, reason="Nicht als Common Stock erkennbar")

        return GateDecision(status=GATE_PASS, reason="Basisregeln erfüllt")
