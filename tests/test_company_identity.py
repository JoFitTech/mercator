"""Tests für Company-Key-Logik und Gate/Profile-Trennung."""

from datetime import datetime, timezone

from src.preprocessing.cleaning import build_company_key, normalize_insider_trade


def test_build_company_key_prefers_cik() -> None:
    assert build_company_key("0000320193", "AAPL") == "CIK:0000320193"


def test_build_company_key_falls_back_to_symbol() -> None:
    assert build_company_key(None, "msft") == "SYM:MSFT"


def test_normalize_trade_sets_gate_and_profile_status_separately() -> None:
    normalized = normalize_insider_trade(
        {"symbol": "AAPL", "companyCik": "0000320193", "securitiesTransacted": "10", "price": "1"},
        fetched_at=datetime.now(timezone.utc),
    )
    assert normalized["gate_status"] == "PENDING"
    assert normalized["profile_status"] == "NOT_REQUESTED"
