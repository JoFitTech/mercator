"""Produktionsnahe Buy-Engine-Regeln für Insider-Trades."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any


STATUS_INVALID = "INVALID"
STATUS_PRE_GATE_FAIL = "PRE_GATE_FAIL"
STATUS_ENRICHED_PARTIAL = "ENRICHED_PARTIAL"
STATUS_REJECT = "REJECT"
STATUS_WATCHLIST = "WATCHLIST"
STATUS_BUY_CANDIDATE = "BUY_CANDIDATE"
STATUS_ACTIONABLE_BUY = "ACTIONABLE_BUY"
STATUS_SELL_WARNING = "SELL_WARNING"
STATUS_MANUAL_REVIEW = "MANUAL_REVIEW"

TR_AVAILABILITY_SCORES = {"CONFIRMED_MATCH": 5, "LIKELY_MATCH": 3, "UNKNOWN": 1, "NOT_FOUND": 0}
TR_TRADABILITY_SCORES = {"GOOD": 5, "OK": 3, "WEAK": 1, "UNKNOWN": 2}

EQUITY_LIKE = {
    "common stock": "OPERATING_COMPANY_EQUITY",
    "class a common stock": "OPERATING_COMPANY_EQUITY",
    "class b common stock": "OPERATING_COMPANY_EQUITY",
    "ordinary shares": "OPERATING_COMPANY_EQUITY",
    "common shares": "OPERATING_COMPANY_EQUITY",
    "shares": "OPERATING_COMPANY_EQUITY",
}
ETF_LIKE = {"etf shares": "ETF", "exchange traded fund": "ETF", "etf": "ETF"}


def normalize_security_type(security_name: str | None) -> str:
    value = str(security_name or "").strip().lower()
    if not value:
        return "UNKNOWN"
    if value in EQUITY_LIKE:
        return EQUITY_LIKE[value]
    if value in ETF_LIKE:
        return ETF_LIKE[value]
    if "adr" in value:
        return "ADR"
    if "fund" in value:
        return "FUND"
    return "UNKNOWN"


def _filing_age_days(trade: dict[str, Any], today: date | None = None) -> int | None:
    filing_date = trade.get("filing_date")
    if filing_date is None:
        return None
    if isinstance(filing_date, datetime):
        d = filing_date.date()
    elif isinstance(filing_date, date):
        d = filing_date
    else:
        return None
    reference = today or datetime.now(UTC).date()
    return max(0, (reference - d).days)


def should_call_exchange_variants(trade: dict[str, Any], preliminary_score: float, context: dict[str, Any] | None = None) -> bool:
    context = context or {}
    gate_ok = str(trade.get("gate_status") or "").upper() in {"PASS", "PENDING"}
    direction = str(trade.get("acquisition_or_disposition") or "").upper()
    tx_code = str(trade.get("transaction_type") or "").strip().upper()[:1]
    tx_class = str(trade.get("transaction_code_class") or "").upper()
    unresolved = bool(context.get("listing_unresolved"))
    in_corridor = preliminary_score >= float(context.get("watchlist_min_score", 55))
    candidate = bool(context.get("trade_republic_candidate"))
    return gate_ok or direction == "A" or in_corridor or unresolved or candidate


@dataclass(slots=True)
class ScoreResult:
    core_insider_score: float
    investability_score: float
    execution_score: float
    trade_republic_score: float
    final_score: float
    final_class: str
    decision_status: str
    caps_applied: list[str]
    filing_age_days: int | None


def score_trade(trade: dict[str, Any]) -> ScoreResult:
    trade_value = float(trade.get("trade_value") or trade.get("trade_value_estimated") or 0)
    market_cap = float(trade.get("market_cap") or 0)
    avg_20d_dollar_volume = float(trade.get("avg_20d_dollar_volume") or 0)
    direction = str(trade.get("acquisition_or_disposition") or "").upper()
    tx_code = str(trade.get("transaction_type") or "").strip().upper()[:1]
    tx_class = str(trade.get("transaction_code_class") or "").upper()
    role = str(trade.get("type_of_owner") or "UNKNOWN").upper()
    filing_age = _filing_age_days(trade)
    security_type = str(trade.get("normalized_instrument_type") or normalize_security_type(trade.get("security_name")))
    technical_state = str(trade.get("technical_state") or "MIXED").upper()
    earnings_distance_days = int(trade.get("earnings_distance_days") or 999)
    tr_availability = str(trade.get("tr_availability_state") or "UNKNOWN").upper()
    tr_tradability = str(trade.get("tr_tradability_state") or "UNKNOWN").upper()
    multi_count = int(trade.get("multi_insider_same_symbol_cluster_count") or 1)
    same_insider = bool(trade.get("same_insider_cluster_flag"))

    core = 0.0
    core += 10 if trade_value >= 5_000_000 else 8 if trade_value >= 1_000_000 else 6 if trade_value >= 500_000 else 4 if trade_value >= 250_000 else 2 if trade_value >= 100_000 else 0
    rel_mcap = (trade_value / market_cap) if market_cap > 0 else 0
    core += 8 if rel_mcap >= 0.005 else 6 if rel_mcap >= 0.002 else 4 if rel_mcap >= 0.0005 else 2 if rel_mcap >= 0.0001 else 0
    rel_vol = (trade_value / avg_20d_dollar_volume) if avg_20d_dollar_volume > 0 else 0
    core += 8 if rel_vol >= 0.20 else 6 if rel_vol >= 0.10 else 4 if rel_vol >= 0.05 else 2 if rel_vol >= 0.01 else 0
    role_scores = {"CEO": 8, "EXECUTIVE_CHAIR": 8, "CFO": 7, "PRESIDENT": 6, "COO": 6, "DIRECTOR": 5, "TEN_PERCENT_OWNER": 4, "OTHER": 2, "UNKNOWN": 0}
    core += role_scores.get(role, 2)
    core += 10 if tx_code == "P" else 0
    core += 2 if tx_class == "SECONDARY_SIGNAL" else 0
    core -= 6 if tx_code == "S" else 0
    core += 4 if same_insider else 2
    core += 5 if multi_count >= 3 else 3 if multi_count >= 2 else 0
    if filing_age is not None:
        core += 4 if filing_age <= 2 else 3 if filing_age <= 5 else 2 if filing_age <= 10 else 1 if filing_age <= 21 else 0

    investability = 0.0
    investability += 4 if market_cap >= 10_000_000_000 else 3 if market_cap >= 2_000_000_000 else 2 if market_cap >= 300_000_000 else 0
    investability += {"STRONG": 4, "NEUTRAL": 2, "WEAK": 0}.get(str(trade.get("balance_sheet_quality") or "NEUTRAL").upper(), 2)
    investability += {"OPERATING_COMPANY_EQUITY": 3, "ETF": 2, "ADR": 1, "FUND": 0}.get(security_type, 0)
    investability += {"STRONG": 4, "NEUTRAL": 2, "WEAK": 0}.get(str(trade.get("sector_business_quality") or "NEUTRAL").upper(), 2)

    execution = 0.0
    execution += 6 if earnings_distance_days > 21 else 4 if earnings_distance_days >= 11 else 2 if earnings_distance_days >= 6 else 1 if earnings_distance_days >= 3 else 0
    execution += {"STRONG": 8, "GOOD": 6, "MIXED": 3, "WEAK": 1, "BROKEN": 0}.get(technical_state, 3)
    rr = float(trade.get("risk_reward_ratio") or 0)
    execution += 6 if rr >= 3.0 else 4 if rr >= 2.0 else 2 if rr >= 1.5 else 0

    tr_score = TR_AVAILABILITY_SCORES.get(tr_availability, 1) + TR_TRADABILITY_SCORES.get(tr_tradability, 2)
    final_score = round(min(100.0, core + investability + execution + tr_score), 2)
    final_class = "A" if final_score >= 85 else "B" if final_score >= 70 else "C" if final_score >= 55 else "D" if final_score >= 40 else "E"

    status = STATUS_REJECT
    caps: list[str] = []
    if tx_code == "S" and (trade_value >= 1_000_000 or role_scores.get(role, 0) >= 6 or multi_count >= 2):
        status = STATUS_SELL_WARNING
    elif tx_code == "P":
        if final_score >= 78 and core >= 34 and execution >= 12 and TR_AVAILABILITY_SCORES.get(tr_availability, 1) >= 3 and (filing_age or 999) <= 21 and earnings_distance_days > 2 and technical_state != "BROKEN":
            status = STATUS_ACTIONABLE_BUY
        elif final_score >= 70:
            status = STATUS_BUY_CANDIDATE
        elif final_score >= 55:
            status = STATUS_WATCHLIST
    if tx_class in {"EXCLUDE_FROM_CORE", "MANUAL_REVIEW"} and tx_code != "S":
        status = STATUS_MANUAL_REVIEW
    if status == STATUS_REJECT and final_score >= 55:
        status = STATUS_WATCHLIST

    if tr_availability == "NOT_FOUND":
        caps.append("TR_NOT_FOUND")
        if status in {STATUS_ACTIONABLE_BUY, STATUS_BUY_CANDIDATE}:
            status = STATUS_WATCHLIST
    if security_type == "FUND":
        caps.append("FUND_CAP")
        if status in {STATUS_ACTIONABLE_BUY, STATUS_BUY_CANDIDATE}:
            status = STATUS_WATCHLIST
    if security_type == "UNKNOWN":
        caps.append("UNKNOWN_SECURITY_CAP")
        status = STATUS_MANUAL_REVIEW if final_score < 55 else STATUS_WATCHLIST
    if technical_state == "BROKEN" or earnings_distance_days <= 2 or (filing_age is not None and filing_age > 21):
        caps.append("EXECUTION_CAP")
        if status in {STATUS_ACTIONABLE_BUY, STATUS_BUY_CANDIDATE}:
            status = STATUS_WATCHLIST
    if filing_age is not None and filing_age > 45:
        status = STATUS_REJECT

    return ScoreResult(
        core_insider_score=round(core, 2),
        investability_score=round(investability, 2),
        execution_score=round(execution, 2),
        trade_republic_score=round(tr_score, 2),
        final_score=final_score,
        final_class=final_class,
        decision_status=status,
        caps_applied=caps,
        filing_age_days=filing_age,
    )
