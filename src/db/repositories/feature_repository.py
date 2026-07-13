"""Repositories fuer berechnete Stock-Analyse-Features."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.db.mysql_client import MySqlClient
from src.models.features import FundamentalFeatures, TechnicalFeatures


class _FeatureRepositoryBase:
    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _rows_to_dicts(cursor: Any, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row, strict=False)) for row in rows]

    @staticmethod
    def _normalize_symbol(value: Any) -> str:
        return str(value or "").strip().upper()

    @staticmethod
    def _normalize_status(value: Any) -> str:
        return str(value or "UNKNOWN").strip().upper() or "UNKNOWN"


class TechnicalFeatureRepository(_FeatureRepositoryBase):
    """Persistiert technische Features pro Symbol und Feature-Datum."""

    @classmethod
    def _build_payload(cls, feature: TechnicalFeatures | dict[str, Any]) -> dict[str, Any]:
        payload = asdict(feature) if isinstance(feature, TechnicalFeatures) else dict(feature)
        symbol = cls._normalize_symbol(payload.get("symbol"))
        if not symbol or not payload.get("feature_date"):
            raise ValueError("Technical feature payload requires symbol and feature_date.")
        return {
            "symbol": symbol,
            "feature_date": payload["feature_date"],
            "momentum_1m": payload.get("momentum_1m"),
            "momentum_3m": payload.get("momentum_3m"),
            "momentum_6m": payload.get("momentum_6m"),
            "sma_20": payload.get("sma_20"),
            "sma_50": payload.get("sma_50"),
            "sma_200": payload.get("sma_200"),
            "volatility_20d": payload.get("volatility_20d"),
            "max_drawdown_1y": payload.get("max_drawdown_1y"),
            "volume_trend_20d": payload.get("volume_trend_20d"),
            "feature_status": cls._normalize_status(payload.get("feature_status")),
            "unavailable_reason": payload.get("unavailable_reason"),
            "input_refreshed_at": payload.get("input_refreshed_at"),
        }

    def upsert_feature(self, feature: TechnicalFeatures | dict[str, Any]) -> None:
        payload = self._build_payload(feature)
        sql = """
            INSERT INTO technical_features (
                symbol, feature_date, momentum_1m, momentum_3m, momentum_6m,
                sma_20, sma_50, sma_200, volatility_20d, max_drawdown_1y,
                volume_trend_20d, feature_status, unavailable_reason, input_refreshed_at
            ) VALUES (
                %(symbol)s, %(feature_date)s, %(momentum_1m)s, %(momentum_3m)s, %(momentum_6m)s,
                %(sma_20)s, %(sma_50)s, %(sma_200)s, %(volatility_20d)s, %(max_drawdown_1y)s,
                %(volume_trend_20d)s, %(feature_status)s, %(unavailable_reason)s, %(input_refreshed_at)s
            )
            ON DUPLICATE KEY UPDATE
                momentum_1m = VALUES(momentum_1m),
                momentum_3m = VALUES(momentum_3m),
                momentum_6m = VALUES(momentum_6m),
                sma_20 = VALUES(sma_20),
                sma_50 = VALUES(sma_50),
                sma_200 = VALUES(sma_200),
                volatility_20d = VALUES(volatility_20d),
                max_drawdown_1y = VALUES(max_drawdown_1y),
                volume_trend_20d = VALUES(volume_trend_20d),
                feature_status = VALUES(feature_status),
                unavailable_reason = VALUES(unavailable_reason),
                input_refreshed_at = VALUES(input_refreshed_at),
                updated_at = CURRENT_TIMESTAMP
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, payload)
            conn.commit()

    def get_latest(self, symbol: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM technical_features WHERE symbol = %s ORDER BY feature_date DESC LIMIT 1"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (self._normalize_symbol(symbol),))
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._rows_to_dicts(cursor, [row])[0]

    def list_features(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        sql = "SELECT * FROM technical_features WHERE symbol = %(symbol)s ORDER BY feature_date DESC LIMIT %(limit)s"
        params = {"symbol": self._normalize_symbol(symbol), "limit": max(1, min(int(limit), 5000))}
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return self._rows_to_dicts(cursor, cursor.fetchall() or [])


class FundamentalFeatureRepository(_FeatureRepositoryBase):
    """Persistiert Fundamental-Features pro Symbol und Berichtsperiode."""

    @classmethod
    def _build_payload(cls, feature: FundamentalFeatures | dict[str, Any]) -> dict[str, Any]:
        payload = asdict(feature) if isinstance(feature, FundamentalFeatures) else dict(feature)
        symbol = cls._normalize_symbol(payload.get("symbol"))
        if not symbol or not payload.get("feature_period"):
            raise ValueError("Fundamental feature payload requires symbol and feature_period.")
        return {
            "symbol": symbol,
            "feature_period": payload["feature_period"],
            "revenue_growth": payload.get("revenue_growth"),
            "earnings_growth": payload.get("earnings_growth"),
            "gross_margin": payload.get("gross_margin"),
            "operating_margin": payload.get("operating_margin"),
            "net_margin": payload.get("net_margin"),
            "valuation_ratio": payload.get("valuation_ratio"),
            "debt_to_equity": payload.get("debt_to_equity"),
            "market_cap": payload.get("market_cap"),
            "feature_status": cls._normalize_status(payload.get("feature_status")),
            "unavailable_reason": payload.get("unavailable_reason"),
            "input_refreshed_at": payload.get("input_refreshed_at"),
        }

    def upsert_feature(self, feature: FundamentalFeatures | dict[str, Any]) -> None:
        payload = self._build_payload(feature)
        sql = """
            INSERT INTO fundamental_features (
                symbol, feature_period, revenue_growth, earnings_growth, gross_margin,
                operating_margin, net_margin, valuation_ratio, debt_to_equity, market_cap,
                feature_status, unavailable_reason, input_refreshed_at
            ) VALUES (
                %(symbol)s, %(feature_period)s, %(revenue_growth)s, %(earnings_growth)s, %(gross_margin)s,
                %(operating_margin)s, %(net_margin)s, %(valuation_ratio)s, %(debt_to_equity)s, %(market_cap)s,
                %(feature_status)s, %(unavailable_reason)s, %(input_refreshed_at)s
            )
            ON DUPLICATE KEY UPDATE
                revenue_growth = VALUES(revenue_growth),
                earnings_growth = VALUES(earnings_growth),
                gross_margin = VALUES(gross_margin),
                operating_margin = VALUES(operating_margin),
                net_margin = VALUES(net_margin),
                valuation_ratio = VALUES(valuation_ratio),
                debt_to_equity = VALUES(debt_to_equity),
                market_cap = VALUES(market_cap),
                feature_status = VALUES(feature_status),
                unavailable_reason = VALUES(unavailable_reason),
                input_refreshed_at = VALUES(input_refreshed_at),
                updated_at = CURRENT_TIMESTAMP
        """
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, payload)
            conn.commit()

    def get_latest(self, symbol: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM fundamental_features WHERE symbol = %s ORDER BY feature_period DESC LIMIT 1"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (self._normalize_symbol(symbol),))
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._rows_to_dicts(cursor, [row])[0]

    def list_features(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        sql = "SELECT * FROM fundamental_features WHERE symbol = %(symbol)s ORDER BY feature_period DESC LIMIT %(limit)s"
        params = {"symbol": self._normalize_symbol(symbol), "limit": max(1, min(int(limit), 5000))}
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return self._rows_to_dicts(cursor, cursor.fetchall() or [])
