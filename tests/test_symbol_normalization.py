from src.domain_rules import normalize_symbol, sanitize_symbol_options


def test_normalize_symbol_filters_invalid_identifiers() -> None:
    assert normalize_symbol(" aapl ") == "AAPL"
    assert normalize_symbol("CIK:0000320193") is None
    assert normalize_symbol("0000320193") is None
    assert normalize_symbol("US0378331005") is None
    assert normalize_symbol("") is None
    assert normalize_symbol(None) is None


def test_sanitize_symbol_options_deduplicates_and_sorts() -> None:
    values = ["aapl", "AAPL", "msft", "CIK:1234", "  ", "123", "TSLA"]
    assert sanitize_symbol_options(values) == ["AAPL", "MSFT", "TSLA"]
