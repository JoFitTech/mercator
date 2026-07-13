"""API3 mapping for historical EOD data and local technical derivations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from statistics import pstdev
from typing import Any

from src.db.repositories.market_signal_cache_repository import MarketSignalCacheRepository

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
    CACHE_TTL_HOURS = 12

    def __init__(self, fmp_client: Any, cache_repo: MarketSignalCacheRepository | None = None) -> None:
        self.fmp_client = fmp_client
        self.cache_repo = cache_repo

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _sorted_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def key_fn(row: dict[str, Any]) -> str:
            return str(row.get("price_date") or row.get("date") or "")
        return sorted(rows, key=key_fn)

    @staticmethod
    def _row_date(row: dict[str, Any]) -> date | None:
        value = row.get("price_date") or row.get("date")
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
        return None

    @classmethod
    def calculate_price_features(cls, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Berechnet technische Features aus lokal gespeicherter Tageshistorie."""

        data = cls._sorted_rows(rows)
        dated_closes: list[tuple[date, float]] = []
        volumes: list[float] = []
        refreshed_at: datetime | None = None
        for row in data:
            row_date = cls._row_date(row)
            close = cls._to_float(row.get("adjusted_close") or row.get("close_price") or row.get("close"))
            volume = cls._to_float(row.get("volume"))
            if row.get("source_refreshed_at") and refreshed_at is None:
                refreshed_at = row.get("source_refreshed_at")
            if row_date is not None and close is not None:
                dated_closes.append((row_date, close))
                if volume is not None:
                    volumes.append(volume)

        if not dated_closes:
            return {
                "feature_date": None,
                "feature_status": "MISSING",
                "unavailable_reason": "No usable price history available.",
                "input_refreshed_at": refreshed_at,
            }

        closes = [close for _, close in dated_closes]
        feature_date = dated_closes[-1][0]
        latest = closes[-1]

        def mean(window: int) -> float | None:
            return (sum(closes[-window:]) / float(window)) if len(closes) >= window else None

        def momentum(offset: int) -> float | None:
            if len(closes) <= offset or closes[-offset] == 0:
                return None
            return (latest / closes[-offset]) - 1.0

        returns = [
            (closes[index] / closes[index - 1]) - 1.0
            for index in range(1, len(closes))
            if closes[index - 1] != 0
        ]
        volatility_20d = pstdev(returns[-20:]) if len(returns) >= 20 else None

        drawdown_window = closes[-252:]
        running_max = drawdown_window[0]
        max_drawdown = 0.0
        for close in drawdown_window:
            running_max = max(running_max, close)
            if running_max:
                max_drawdown = min(max_drawdown, (close / running_max) - 1.0)

        volume_trend_20d = None
        if len(volumes) >= 40:
            prior = sum(volumes[-40:-20]) / 20.0
            recent = sum(volumes[-20:]) / 20.0
            if prior:
                volume_trend_20d = (recent / prior) - 1.0

        status = "READY" if len(closes) >= 200 else "INCOMPLETE"
        reason = None if status == "READY" else f"Only {len(closes)} usable price rows available; 200 required."
        return {
            "feature_date": feature_date,
            "momentum_1m": momentum(22),
            "momentum_3m": momentum(63),
            "momentum_6m": momentum(126),
            "sma_20": mean(20),
            "sma_50": mean(50),
            "sma_200": mean(200),
            "volatility_20d": volatility_20d,
            "max_drawdown_1y": max_drawdown if len(drawdown_window) >= 2 else None,
            "volume_trend_20d": volume_trend_20d,
            "feature_status": status,
            "unavailable_reason": reason,
            "input_refreshed_at": refreshed_at,
        }

    def load_signal(self, symbol: str, today: date | None = None) -> HistoricalSignal:
        reference = today or datetime.now(UTC).date()
        from_date = reference - timedelta(days=self.LOOKBACK_DAYS)
        if self.cache_repo is not None:
            cached = self.cache_repo.get_symbol_cache(symbol)
            if cached and self._is_cache_fresh(cached, reference):
                return HistoricalSignal(
                    avg_20d_volume=self._to_float(cached.get("avg_20d_volume")),
                    avg_20d_dollar_volume=self._to_float(cached.get("avg_20d_dollar_volume")),
                    sma_50=self._to_float(cached.get("sma_50")),
                    sma_200=self._to_float(cached.get("sma_200")),
                    momentum_3m=self._to_float(cached.get("momentum_3m")),
                    momentum_6m=self._to_float(cached.get("momentum_6m")),
                    technical_state=str(cached.get("technical_state") or "MIXED"),
                    liquidity_state=str(cached.get("liquidity_state") or "LOW"),
                )
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

        signal = HistoricalSignal(
            avg_20d_volume=avg20_vol,
            avg_20d_dollar_volume=avg20_dollar,
            sma_50=sma50,
            sma_200=sma200,
            momentum_3m=m3,
            momentum_6m=m6,
            technical_state=technical_state,
            liquidity_state=liquidity_state,
        )
        if self.cache_repo is not None:
            self.cache_repo.upsert_symbol_cache(
                {
                    "symbol": symbol,
                    "lookback_from": from_date,
                    "lookback_to": reference,
                    "avg_20d_volume": signal.avg_20d_volume,
                    "avg_20d_dollar_volume": signal.avg_20d_dollar_volume,
                    "sma_50": signal.sma_50,
                    "sma_200": signal.sma_200,
                    "momentum_3m": signal.momentum_3m,
                    "momentum_6m": signal.momentum_6m,
                    "technical_state": signal.technical_state,
                    "liquidity_state": signal.liquidity_state,
                    "source_refreshed_at": datetime.now(UTC),
                    "raw_row_count": len(data),
                    "cache_status": "READY" if data else "EMPTY",
                }
            )
        return signal

    def _is_cache_fresh(self, cached: dict[str, Any], reference: date) -> bool:
        refreshed = cached.get("source_refreshed_at") or cached.get("refreshed_at")
        if not isinstance(refreshed, datetime):
            return False
        if refreshed.tzinfo is None:
            refreshed = refreshed.replace(tzinfo=UTC)
        if datetime.now(UTC) - refreshed > timedelta(hours=self.CACHE_TTL_HOURS):
            return False
        cached_to_date = cached.get("lookback_to") or cached.get("to_date")
        return isinstance(cached_to_date, date) and cached_to_date >= reference
