from __future__ import annotations

import csv
import io
import re
from typing import Iterable

from src.domain.trade_republic_universe import (
    TradeRepublicUniverseInstrument,
    TradeRepublicUniverseParseResult,
)

ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


def validate_isin(value: str | None) -> bool:
    isin = str(value or "").strip().upper().replace(" ", "")
    return bool(ISIN_PATTERN.match(isin))


def normalize_instrument_name(value: str | None) -> str:
    raw = str(value or "").strip()
    return " ".join(raw.split())


def _first_value(row: dict[str, object], aliases: Iterable[str]) -> str:
    alias_set = {a.lower() for a in aliases}
    for key, value in row.items():
        if str(key).strip().lower() in alias_set:
            return str(value or "").strip()
    return ""


def parse_trade_republic_csv(raw_text: str) -> TradeRepublicUniverseParseResult:
    stripped = str(raw_text or "").strip()
    if not stripped:
        return TradeRepublicUniverseParseResult([], 0, 0, 0)

    try:
        dialect = csv.Sniffer().sniff(stripped[:2048], delimiters=",;\t")
    except Exception:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(raw_text), dialect=dialect)
    total_rows = 0
    invalid_rows = 0
    dedupe_by_isin: dict[str, TradeRepublicUniverseInstrument] = {}

    for row in reader:
        total_rows += 1
        isin = _first_value(row, ["isin"]).upper().replace(" ", "")
        if not validate_isin(isin):
            invalid_rows += 1
            continue

        symbol = _first_value(row, ["symbol", "ticker"]).upper() or None
        name = normalize_instrument_name(_first_value(row, ["instrument_name", "name", "title"])) or None
        country = _first_value(row, ["country", "land"]) or None
        asset_class = _first_value(row, ["asset_class", "type", "assetclass"]) or None

        dedupe_by_isin[isin] = TradeRepublicUniverseInstrument(
            isin=isin,
            symbol=symbol,
            instrument_name=name,
            country=country,
            asset_class=asset_class,
            normalized_name=normalize_instrument_name(name),
        )

    instruments = [dedupe_by_isin[k] for k in sorted(dedupe_by_isin.keys())]
    return TradeRepublicUniverseParseResult(
        instruments=instruments,
        total_rows=total_rows,
        valid_rows=len(instruments),
        invalid_rows=invalid_rows,
    )


