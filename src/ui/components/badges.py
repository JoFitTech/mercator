"""Zentrale Badge-Mappings fuer Gate/Validation/Score/Decision/Tx-Code.

Wichtig: Status niemals nur ueber Farbe kommunizieren. Die Label sind immer textuell.
"""

from __future__ import annotations

from src.ui.components.status_badges import status_badge


def _as_text(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    return text if text else fallback


def render_gate_badge(status: str) -> None:
    normalized = _as_text(status, "UNBEKANNT").upper()
    style = "PASS" if normalized == "PASS" else "FAIL" if normalized in {"FAIL", "PRE_GATE_FAIL"} else "PENDING"
    status_badge(f"GATE: {normalized}", status_type=style)


def render_validation_badge(status: str) -> None:
    normalized = _as_text(status, "UNBEKANNT").upper()
    style = "PASS" if normalized == "VALID" else "FAIL" if normalized in {"INVALID", "PRICE_INVALID"} else "INFO"
    status_badge(f"VALIDATION: {normalized}", status_type=style)


def render_score_badge(score_class: str, score_value: float | None = None) -> None:
    cls = _as_text(score_class, "N/A").upper()
    score_txt = f" ({score_value:.1f})" if isinstance(score_value, (int, float)) else ""
    style = "PASS" if cls in {"A", "B"} else "PENDING" if cls == "C" else "WARNING" if cls == "D" else "FAIL"
    status_badge(f"SCORE: {cls}{score_txt}", status_type=style)


def render_decision_badge(decision: str) -> None:
    normalized = _as_text(decision, "UNKNOWN").upper()
    if normalized in {"ACTIONABLE_BUY", "BUY_CANDIDATE"}:
        style = "PASS"
    elif normalized in {"WATCHLIST", "MANUAL_REVIEW"}:
        style = "WARNING"
    elif normalized in {"SELL_WARNING", "REJECT", "PRE_GATE_FAIL", "INVALID"}:
        style = "FAIL"
    else:
        style = "INFO"
    status_badge(f"DECISION: {normalized}", status_type=style)


def render_tx_code_badge(code_class: str) -> None:
    normalized = _as_text(code_class, "UNKNOWN").upper()
    if normalized == "CORE_BUY":
        style = "PASS"
        label = "TX: CORE BUY"
    elif normalized == "CORE_SELL":
        style = "FAIL"
        label = "TX: CORE SELL"
    elif normalized == "SECONDARY_SIGNAL":
        style = "WARNING"
        label = "TX: SECONDARY"
    elif normalized == "MANUAL_REVIEW":
        style = "INFO"
        label = "TX: MANUAL REVIEW"
    else:
        style = "NEUTRAL"
        label = "TX: EXCLUDED"
    status_badge(label, status_type=style)

