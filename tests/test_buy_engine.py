from __future__ import annotations

from datetime import datetime, timedelta, UTC

from src.services.buy_engine import normalize_security_type, score_trade, should_call_exchange_variants


def _base_trade() -> dict:
    return {
        "security_name": "Common Stock",
        "normalized_instrument_type": "OPERATING_COMPANY_EQUITY",
        "trade_value_estimated": 2_000_000,
        "market_cap": 12_000_000_000,
        "avg_20d_dollar_volume": 10_000_000,
        "type_of_owner": "CEO",
        "acquisition_or_disposition": "A",
        "same_insider_cluster_flag": True,
        "multi_insider_same_symbol_cluster_count": 3,
        "balance_sheet_quality": "STRONG",
        "sector_business_quality": "STRONG",
        "technical_state": "GOOD",
        "earnings_distance_days": 12,
        "risk_reward_ratio": 2.5,
        "tr_availability_state": "CONFIRMED_MATCH",
        "tr_tradability_state": "GOOD",
        "filing_date": datetime.now(UTC) - timedelta(days=1),
    }


def test_security_normalization_allows_etf_and_unknown() -> None:
    assert normalize_security_type("ETF Shares") == "ETF"
    assert normalize_security_type("Mystery Instrument") == "UNKNOWN"


def test_high_score_a_with_tr_match_is_actionable_buy() -> None:
    result = score_trade(_base_trade())
    assert result.decision_status == "ACTIONABLE_BUY"
    assert result.final_score >= 78


def test_high_score_with_tr_not_found_is_capped_to_watchlist() -> None:
    trade = _base_trade()
    trade["tr_availability_state"] = "NOT_FOUND"
    result = score_trade(trade)
    assert result.decision_status == "WATCHLIST"


def test_disposition_large_value_is_sell_warning() -> None:
    trade = _base_trade()
    trade["acquisition_or_disposition"] = "D"
    trade["trade_value_estimated"] = 1_200_000
    result = score_trade(trade)
    assert result.decision_status == "SELL_WARNING"


def test_filing_age_and_earnings_caps_force_watchlist() -> None:
    trade = _base_trade()
    trade["filing_date"] = datetime.now(UTC) - timedelta(days=22)
    trade["earnings_distance_days"] = 2
    result = score_trade(trade)
    assert result.decision_status == "WATCHLIST"


def test_filing_age_over_45_rejects() -> None:
    trade = _base_trade()
    trade["filing_date"] = datetime.now(UTC) - timedelta(days=50)
    result = score_trade(trade)
    assert result.decision_status == "REJECT"


def test_exchange_variants_trigger_only_for_shortlist_or_resolution_needs() -> None:
    base = {"gate_status": "FAIL", "acquisition_or_disposition": "D"}
    assert should_call_exchange_variants(base, preliminary_score=20, context={}) is False
    assert should_call_exchange_variants(base, preliminary_score=60, context={}) is True
