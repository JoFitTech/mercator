"""API2 enrichment with selective CIK fallback resolution."""

from __future__ import annotations

from typing import Any


class IdentifierResolutionService:
    def __init__(self, fmp_client: Any) -> None:
        self.fmp_client = fmp_client

    def resolve_cik(self, symbol: str) -> str | None:
        candidates = self.fmp_client.fetch_search_cik(symbol)
        if not candidates:
            return None
        first = candidates[0]
        cik = first.get("cik") or first.get("companyCik")
        return str(cik) if cik else None


class CompanyProfileEnrichmentService:
    def __init__(self, fmp_client: Any, identifier_resolution: IdentifierResolutionService | None = None) -> None:
        self.fmp_client = fmp_client
        self.identifier_resolution = identifier_resolution or IdentifierResolutionService(fmp_client)

    def fetch_profile(self, symbol: str) -> dict[str, Any] | None:
        profile = self.fmp_client.fetch_company_profile(symbol)
        if profile and (profile.get("companyName") or profile.get("company_name")):
            return profile

        cik = self.identifier_resolution.resolve_cik(symbol)
        if not cik:
            return profile
        by_cik = self.fmp_client.fetch_company_profile_by_cik(cik)
        return by_cik or profile

    @staticmethod
    def map_profile_fields(profile: dict[str, Any] | None) -> dict[str, Any]:
        if not profile:
            return {}
        return {
            "company_name": profile.get("companyName") or profile.get("company_name"),
            "market_cap": profile.get("mktCap") or profile.get("marketCap") or profile.get("market_cap"),
            "industry": profile.get("industry"),
            "cik": profile.get("cik") or profile.get("companyCik"),
            "isin": profile.get("isin"),
            "cusip": profile.get("cusip"),
            "exchange": profile.get("exchange"),
            "country": profile.get("country"),
            "sector": profile.get("sector"),
            "profile_price": profile.get("price"),
        }
