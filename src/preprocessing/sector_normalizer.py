"""Hilfsfunktionen zur Normalisierung von Sektorbezeichnungen."""

from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)

CANONICAL_SECTORS = [
    "Technology",
    "Healthcare",
    "Financials",
    "Industrials",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Utilities",
    "Materials",
    "Real Estate",
    "Communication Services",
]

# Mapping von verschiedenen Provider-Bezeichnungen auf die kanonische Form
SECTOR_MAPPING = {
    # Technology
    "Technology": "Technology",
    "Information Technology": "Technology",
    "Software & Services": "Technology",
    "Hardware": "Technology",
    "Semiconductors": "Technology",
    
    # Healthcare
    "Healthcare": "Healthcare",
    "Health Care": "Healthcare",
    "Biotechnology": "Healthcare",
    "Pharmaceuticals": "Healthcare",
    
    # Financials
    "Financials": "Financials",
    "Financial Services": "Financials",
    "Banking": "Financials",
    "Insurance": "Financials",
    "Finance": "Financials",
    
    # Industrials
    "Industrials": "Industrials",
    "Industrial Goods": "Industrials",
    "Capital Goods": "Industrials",
    "Transportation": "Industrials",
    "Aerospace & Defense": "Industrials",
    
    # Consumer Discretionary
    "Consumer Discretionary": "Consumer Discretionary",
    "Consumer Cyclical": "Consumer Discretionary",
    "Retail": "Consumer Discretionary",
    "Automobiles & Components": "Consumer Discretionary",
    
    # Consumer Staples
    "Consumer Staples": "Consumer Staples",
    "Consumer Non-Cyclical": "Consumer Staples",
    "Food, Beverage & Tobacco": "Consumer Staples",
    "Household & Personal Products": "Consumer Staples",
    
    # Energy
    "Energy": "Energy",
    "Oil & Gas": "Energy",
    "Renewable Energy": "Energy",
    
    # Utilities
    "Utilities": "Utilities",
    "Electric Utilities": "Utilities",
    "Gas Utilities": "Utilities",
    
    # Materials
    "Materials": "Materials",
    "Basic Materials": "Materials",
    "Chemicals": "Materials",
    "Mining": "Materials",
    
    # Real Estate
    "Real Estate": "Real Estate",
    "Property": "Real Estate",
    "REITs": "Real Estate",
    
    # Communication Services
    "Communication Services": "Communication Services",
    "Telecommunications": "Communication Services",
    "Media": "Communication Services",
    "Entertainment": "Communication Services",
}

# Mapping für SIC-Codes oder Beschreibungen (Beispielhaft)
SIC_SECTOR_MAPPING = {
    "10": "Materials",  # Mining
    "12": "Energy",     # Coal
    "13": "Energy",     # Oil & Gas
    "15": "Real Estate", # Construction
    "20": "Consumer Staples", # Food
    "28": "Materials",  # Chemicals/Pharma
    "35": "Technology", # Machinery/Computing
    "36": "Technology", # Electrical/Electronic
    "37": "Industrials", # Transportation Equipment
    "38": "Healthcare", # Instruments/Medical
    "48": "Communication Services", # Communication
    "49": "Utilities",  # Electric/Gas/Sanitary
    "60": "Financials", # Banking
    "65": "Real Estate", # Real Estate
    "73": "Technology", # Business Services (Software)
    "80": "Healthcare", # Health Services
}

def normalize_sector(raw_sector: str | None, sic_code: str | None = None, sic_description: str | None = None) -> tuple[str | None, str]:
    """Normalisiert einen rohen Sektorwert in die kanonische Taxonomie.
    
    Returns:
        tuple[str | None, str]: (normalized_sector, resolution_method)
    """
    if not raw_sector and not sic_code and not sic_description:
        return None, "NONE"

    # 1. Direkte Sektor-Normalisierung
    if raw_sector:
        s = raw_sector.strip()
        if s.lower() in [v.lower() for v in ["null", "none", "unknown", "n/a", ""]]:
            pass # Weiter zu SIC
        else:
            # Versuche Mapping
            for key, val in SECTOR_MAPPING.items():
                if s.lower() == key.lower():
                    return val, "DIRECT_MAPPING"
            # Fallback: Wenn es in CANONICAL_SECTORS ist, nimm es direkt
            for can in CANONICAL_SECTORS:
                if s.lower() == can.lower():
                    return can, "CANONICAL_MATCH"

    # 2. SIC-Code Mapping
    if sic_code:
        prefix = sic_code[:2]
        if prefix in SIC_SECTOR_MAPPING:
            return SIC_SECTOR_MAPPING[prefix], "SIC_CODE_MAPPING"

    # 3. SIC-Description Mapping (sehr einfach gehalten)
    if sic_description:
        desc = sic_description.lower()
        for key, val in SECTOR_MAPPING.items():
            if key.lower() in desc:
                return val, "SIC_DESCRIPTION_KEYWORD"

    return None, "UNRESOLVED"
