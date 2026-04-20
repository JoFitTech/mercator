"""Domainregeln für Symbole sowie Score-/Gate-Policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable

_CIK_PREFIX_RE = re.compile(r"^CIK\s*:\s*\d+", re.IGNORECASE)
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


@dataclass(frozen=True, slots=True)
class ScoreGatePolicy:
    """Zentrale, persistierbare Schwellen und Gate-Regeln."""

    score_threshold_fail_max: float = 70.0
    score_threshold_hold_min: float = 70.0
    score_threshold_pass_min: float = 90.0
    fail_label: str = "FAIL"
    hold_label: str = "HOLD"
    pass_label: str = "PASS"
    fail_color: str = "#ef4444"
    hold_color: str = "#facc15"
    pass_color: str = "#22c55e"

    gate_validation_status_required: str = "VALID"
    gate_form_type_required: str = "4"
    gate_security_name_required: str = ""
    gate_allowed_acquisition_or_disposition: tuple[str, ...] = ("A", "D")
    gate_excluded_transaction_types: tuple[str, ...] = ("A-Award", "M-Exempt")
    gate_min_trade_value: int = 100_000

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_symbol(raw_value: Any) -> str | None:
    """Normalisiert Symbole robust; verwirft CIK/ISIN/numerische IDs."""

    if raw_value is None:
        return None
    value = str(raw_value).strip().upper()
    if not value:
        return None
    if _CIK_PREFIX_RE.match(value):
        return None
    if value.startswith("CIK"):
        return None
    if value.isdigit():
        return None
    if _ISIN_RE.match(value):
        return None
    if ":" in value:
        return None
    return value


def sanitize_symbol_options(values: Iterable[Any]) -> list[str]:
    """Erzeugt alphabetisch sortierte, deduplizierte Ticker-Optionen."""

    normalized = {symbol for value in values if (symbol := normalize_symbol(value))}
    return sorted(normalized)


def classify_score(score: Any, policy: ScoreGatePolicy) -> tuple[str, str]:
    """Klassifiziert einen Score in FAIL/HOLD/PASS inkl. Farbwert."""

    try:
        numeric_score = float(score)
    except (TypeError, ValueError):
        return policy.fail_label, policy.fail_color

    if numeric_score >= float(policy.score_threshold_pass_min):
        return policy.pass_label, policy.pass_color
    if numeric_score >= float(policy.score_threshold_hold_min):
        return policy.hold_label, policy.hold_color
    return policy.fail_label, policy.fail_color


def compute_discrete_score(trade: dict[str, Any]) -> tuple[float, str]:
    """Berechnet einen diskreten Mercator-Score (0-100) und eine Klasse (A-E).
    
    Logik:
    - Trade Value (max 50): Stufen 50k, 100k, 500k, 1M, 10M
    - Direction (max 20): BUY (+20), SELL (+5)
    - Role (max 20): CEO/CFO/Officer (+20), Director (+15), Other (+5)
    - Market Cap (max 5): > 1B (+5)
    - Validation (max 5): VALID (+5)
    """
    points = 0.0
    
    # 1. Trade Value
    value = float(trade.get("trade_value_estimated") or 0)
    if value >= 10_000_000: points += 50
    elif value >= 1_000_000: points += 40
    elif value >= 500_000: points += 30
    elif value >= 100_000: points += 20
    elif value >= 50_000: points += 10
    
    # 2. Direction
    direction = str(trade.get("acquisition_or_disposition") or "").upper()
    if direction in ("A", "BUY"): points += 20
    elif direction in ("D", "SELL"): points += 5
    
    # 3. Insider Role
    owner = str(trade.get("type_of_owner") or "").lower()
    if any(token in owner for token in ("ceo", "cfo", "officer", "president")): points += 20
    elif "director" in owner: points += 15
    else: points += 5
    
    # 4. Market Cap
    mcap = float(trade.get("market_cap") or 0)
    if mcap >= 1_000_000_000: points += 5
    
    # 5. Validation
    if str(trade.get("validation_status") or "").upper() == "VALID": points += 5
    
    score = min(100.0, points)
    
    # Klasse
    if score >= 80: cls = "A"
    elif score >= 60: cls = "B"
    elif score >= 40: cls = "C"
    elif score >= 20: cls = "D"
    else: cls = "E"
    
    return score, cls
