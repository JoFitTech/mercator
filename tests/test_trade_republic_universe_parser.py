from __future__ import annotations

from src.preprocessing.trade_republic_universe_parser import parse_trade_republic_csv, validate_isin


def test_parser_supports_tab_delimiter() -> None:
    payload = "isin\tsymbol\tinstrument_name\nUS0378331005\tAAPL\tApple Inc.\n"
    parsed = parse_trade_republic_csv(payload)
    assert parsed.valid_rows == 1
    assert parsed.instruments[0].symbol == "AAPL"


def test_parser_deduplicates_isin_deterministically() -> None:
    payload = (
        "isin,symbol,instrument_name\n"
        "US0378331005,AAPL,Apple Inc.\n"
        "US0378331005,AAPL,Apple Inc. Class A\n"
    )
    parsed = parse_trade_republic_csv(payload)
    assert parsed.valid_rows == 1
    assert parsed.instruments[0].instrument_name == "Apple Inc. Class A"


def test_validate_isin_rejects_invalid() -> None:
    assert validate_isin("US0378331005") is True
    assert validate_isin("BAD") is False

