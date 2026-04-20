"""Service zur Anreicherung von Unternehmensprofilen aus mehreren Quellen."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.data_sources.alpha_vantage_client import AlphaVantageClient
from src.data_sources.fmp_client import FmpClient
from src.data_sources.polygon_client import PolygonClient
from src.models.company import Company
from src.preprocessing.sector_normalizer import normalize_sector

LOGGER = logging.getLogger(__name__)

class CompanyEnrichmentService:
    """Implementiert die mehrstufige sektorbezogene Auflösung."""

    def __init__(
        self,
        fmp_client: FmpClient,
        alpha_vantage_client: AlphaVantageClient | None = None,
        polygon_client: PolygonClient | None = None
    ) -> None:
        self.fmp_client = fmp_client
        self.alpha_vantage_client = alpha_vantage_client
        self.polygon_client = polygon_client

    def enrich_company_profile(self, symbol: str, existing_company: Company | None = None) -> Company:
        """Führt die Enrichment-Kette für ein Symbol aus.
        
        Kette:
        1. FMP (Primary)
        2. Alpha Vantage (Secondary)
        3. Polygon (Tertiary)
        """
        company = existing_company or Company(symbol=symbol)
        
        # 1. FMP
        fmp_profile = self.fmp_client.fetch_company_profile(symbol)
        if fmp_profile:
            self._apply_fmp_data(company, fmp_profile)
            if company.sector_resolution_status == "RESOLVED":
                return company

        # 2. Alpha Vantage
        if self.alpha_vantage_client:
            av_profile = self.alpha_vantage_client.fetch_company_overview(symbol)
            if av_profile:
                self._apply_alpha_vantage_data(company, av_profile)
                if company.sector_resolution_status == "RESOLVED":
                    return company

        # 3. Polygon
        if self.polygon_client:
            poly_profile = self.polygon_client.fetch_ticker_details(symbol)
            if poly_profile:
                self._apply_polygon_data(company, poly_profile)

        return company

    def _apply_fmp_data(self, company: Company, data: dict[str, Any]) -> None:
        """Mapping für FMP Daten."""
        company.company_name = company.company_name or data.get("companyName")
        company.sector_raw = data.get("sector")
        company.industry = company.industry or data.get("industry")
        company.market_cap = company.market_cap or data.get("mktCap") or data.get("marketCap")

        normalized, method = normalize_sector(company.sector_raw)
        if normalized:
            company.sector_normalized = normalized
            company.sector = normalized
            company.sector_resolution_status = "RESOLVED"
            company.sector_resolution_method = f"FMP_{method}"
            company.sector_source = "FMP"
            company.profile_provider = "FMP"
            company.profile_enriched_at = datetime.now(timezone.utc)

    def _apply_alpha_vantage_data(self, company: Company, data: dict[str, Any]) -> None:
        """Mapping für Alpha Vantage Daten."""
        company.company_name = company.company_name or data.get("Name")
        raw_sector = data.get("Sector")
        
        normalized, method = normalize_sector(raw_sector)
        if normalized:
            company.sector_raw = raw_sector
            company.sector_normalized = normalized
            company.sector = normalized
            company.sector_resolution_status = "RESOLVED"
            company.sector_resolution_method = f"ALPHA_VANTAGE_{method}"
            company.sector_source = "Alpha Vantage"
            company.profile_provider = company.profile_provider or "Alpha Vantage"
            company.profile_enriched_at = datetime.now(timezone.utc)

    def _apply_polygon_data(self, company: Company, data: dict[str, Any]) -> None:
        """Mapping für Polygon Daten."""
        company.company_name = company.company_name or data.get("name")
        sic_code = data.get("sic_code")
        sic_desc = data.get("sic_description")
        
        # Polygon hat oft keinen direkten "sector" String in v3 ticker details, sondern SIC
        normalized, method = normalize_sector(None, sic_code=str(sic_code) if sic_code else None, sic_description=sic_desc)
        if normalized:
            company.sector_raw = sic_desc
            company.sector_normalized = normalized
            company.sector = normalized
            company.sector_resolution_status = "RESOLVED"
            company.sector_resolution_method = f"POLYGON_{method}"
            company.sector_source = "Polygon"
            company.profile_provider = company.profile_provider or "Polygon"
            company.profile_enriched_at = datetime.now(timezone.utc)
