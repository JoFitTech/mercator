from __future__ import annotations

from src.services.company_profile_enrichment_service import CompanyProfileEnrichmentService
from src.ui.components.formatting import (
    _is_incomplete_profile,
    _normalize_website_url,
)
from src.ui.pages.companies_page import _refresh_company_profile


def test_is_incomplete_profile_detects_missing_sector() -> None:
    profile = {
        "profile_status": "FETCHED",
        "company_name": "Apple Inc.",
        "industry": "Consumer Electronics",
        "market_cap": 1_000_000,
        "sector": None,
        "description": "desc",
    }
    assert _is_incomplete_profile(profile) is True


def test_is_incomplete_profile_detects_missing_description() -> None:
    profile = {
        "profile_status": "FETCHED",
        "company_name": "Apple Inc.",
        "industry": "Consumer Electronics",
        "market_cap": 1_000_000,
        "sector": "Technology",
        "description": "",
    }
    assert _is_incomplete_profile(profile) is True


def test_is_incomplete_profile_detects_failed_status() -> None:
    profile = {
        "profile_status": "FAILED",
        "company_name": "Apple Inc.",
        "industry": "Consumer Electronics",
        "market_cap": 1_000_000,
        "sector": "Technology",
        "description": "desc",
    }
    assert _is_incomplete_profile(profile) is True


def test_is_incomplete_profile_false_for_complete_profile() -> None:
    profile = {
        "profile_status": "FETCHED",
        "company_name": "Apple Inc.",
        "industry": "Consumer Electronics",
        "market_cap": 1_000_000,
        "sector": "Technology",
        "description": "desc",
    }
    assert _is_incomplete_profile(profile) is False


def test_normalize_website_url() -> None:
    assert _normalize_website_url("example.com") == "https://example.com"
    assert _normalize_website_url("https://example.com") == "https://example.com"
    assert _normalize_website_url("") is None
    assert _normalize_website_url(None) is None


def test_refresh_service_only_runs_in_explicit_helper_path() -> None:
    class _ImportServiceStub:
        def __init__(self) -> None:
            self.calls = 0

        def refresh_company_profile_for_symbol(self, symbol: str):
            self.calls += 1
            return {"ok": True, "symbol": symbol}

    service = _ImportServiceStub()
    assert service.calls == 0

    result = _refresh_company_profile(service, "AAPL")

    assert service.calls == 1
    assert result["ok"] is True


def test_company_description_mapping_uses_description_field() -> None:
    mapped = CompanyProfileEnrichmentService.map_profile_fields(
        {"description": "Apple description", "companyName": "Apple Inc."}
    )
    assert mapped["description"] == "Apple description"


def test_company_description_mapping_missing_description_maps_none() -> None:
    mapped = CompanyProfileEnrichmentService.map_profile_fields(
        {"companyName": "Apple Inc."}
    )
    assert mapped.get("description") is None

