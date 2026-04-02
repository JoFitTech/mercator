"""Tests für Normalisierung und Deduplizierung von Insider-Trades."""

from src.preprocessing.insider_trade_cleaner import build_dedupe_key, normalize_insider_trade


def test_build_dedupe_key_is_stable_for_identical_input() -> None:
    """Identische Kernfelder müssen denselben Dedupe-Key ergeben."""
    normalized = {
        "symbol": "AAPL",
        "filing_date": "2025-01-01",
        "transaction_date": "2024-12-31",
        "reporting_cik": "1",
        "company_cik": "2",
        "transaction_type": "P-Purchase",
        "qty": 100.0,
        "price": 150.5,
    }
    assert build_dedupe_key(normalized) == build_dedupe_key(normalized)


def test_normalize_insider_trade_maps_and_parses_required_fields() -> None:
    """Rohdaten sollen korrekt in das Projektschema transformiert werden."""
    raw = {
        "symbol": " msft ",
        "filingDate": "2025-03-01",
        "transactionDate": "2025-02-27",
        "reportingCik": "111",
        "companyCik": "222",
        "transactionType": "P-Purchase",
        "securitiesTransacted": "123",
        "price": "321.5",
        "url": "https://example.test/doc",
    }
    result = normalize_insider_trade(raw)

    assert result["symbol"] == "MSFT"
    assert result["qty"] == 123.0
    assert result["price"] == 321.5
    assert result["source_url"] == "https://example.test/doc"
    assert result["dedupe_key"]
