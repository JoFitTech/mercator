"""API3 mapping for historical EOD data and local technical derivations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any


@dataclass(slots=True)
class HistoricalSignal:
    avg_20d_volume: float | None
    avg_20d_dollar_volume: float | None
    sma_50: float | None
    sma_200: float | None
    momentum_3m: float | None
    momentum_6m: float | None
    technical_state: str
    liquidity_state: str


class HistoricalMarketDataService:
    LOOKBACK_DAYS = 500

    def __init__(self, fmp_client: Any) -> None:
        self.fmp_client = fmp_client

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _sorted_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def key_fn(row: dict[str, Any]) -> str:
            return str(row.get("date") or "")
        return sorted(rows, key=key_fn)

    def load_signal(self, symbol: str, today: date | None = None) -> HistoricalSignal:
        reference = today or datetime.now(UTC).date()
        from_date = reference - timedelta(days=self.LOOKBACK_DAYS)
        rows = self.fmp_client.fetch_historical_price_eod_full(
            symbol=symbol,
            date_from=from_date.isoformat(),
            date_to=reference.isoformat(),
        )
        data = self._sorted_rows(rows)
        closes = [self._to_float(x.get("close")) for x in data]
        volumes = [self._to_float(x.get("volume")) for x in data]
        closes = [x for x in closes if x is not None]
        volumes = [x for x in volumes if x is not None]

        avg20_vol = (sum(volumes[-20:]) / len(volumes[-20:])) if len(volumes) >= 1 else None

        dollar_vols: list[float] = []
        for row in data:
            c = self._to_float(row.get("close"))
            v = self._to_float(row.get("volume"))
            if c is not None and v is not None:
                dollar_vols.append(c * v)
        avg20_dollar = (sum(dollar_vols[-20:]) / len(dollar_vols[-20:])) if dollar_vols else None

        sma50 = (sum(closes[-50:]) / 50.0) if len(closes) >= 50 else None
        sma200 = (sum(closes[-200:]) / 200.0) if len(closes) >= 200 else None
        latest = closes[-1] if closes else None
        m3 = ((latest / closes[-63]) - 1.0) if latest is not None and len(closes) > 63 and closes[-63] else None
        m6 = ((latest / closes[-126]) - 1.0) if latest is not None and len(closes) > 126 and closes[-126] else None

        technical_state = "MIXED"
        if latest is not None and sma50 is not None and sma200 is not None:
            if latest > sma50 > sma200:
                technical_state = "STRONG"
            elif latest < sma50 < sma200:
                technical_state = "WEAK"

        liquidity_state = "LOW"
        if (avg20_dollar or 0) >= 20_000_000:
            liquidity_state = "HIGH"
        elif (avg20_dollar or 0) >= 5_000_000:
            liquidity_state = "MEDIUM"

        return HistoricalSignal(
            avg_20d_volume=avg20_vol,
            avg_20d_dollar_volume=avg20_dollar,
            sma_50=sma50,
            sma_200=sma200,
            momentum_3m=m3,
            momentum_6m=m6,
            technical_state=technical_state,
            liquidity_state=liquidity_state,
        )
