"""Security normalization for final instrument scope (Stocks + ETFs only)."""

from __future__ import annotations


class SecurityNormalizationService:
    ALLOWED = {"STOCK", "ETF"}

    @staticmethod
    def normalize(security_name: str | None) -> str:
        value = str(security_name or "").strip().lower()
        if not value:
            return "UNKNOWN"
        if "etf" in value or "exchange traded fund" in value:
            return "ETF"
        if "adr" in value or "depositary" in value:
            return "ADR"
        if "preferred" in value:
            return "PREFERRED_SHARE"
        if "note" in value:
            return "NOTE"
        if "fund" in value:
            return "FUND"
        if any(token in value for token in ("common stock", "ordinary share", "common share", "stock", "share")):
            return "STOCK"
        return "UNKNOWN"

    @classmethod
    def is_allowed(cls, normalized_type: str | None) -> bool:
        return str(normalized_type or "").upper() in cls.ALLOWED
