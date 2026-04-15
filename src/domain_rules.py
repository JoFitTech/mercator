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
    gate_security_name_required: str = "Common Stock"
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
