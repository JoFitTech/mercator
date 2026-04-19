import pytest
import pandas as pd
from datetime import datetime, timezone
from src.preprocessing.cleaning import normalize_insider_trade
from src.services.import_service import ImportService
from src.services.dashboard_service import DashboardService
# P0.4: format_mcap ist jetzt in dataframe_utils (ticker_detail_page existiert nicht mehr)
from src.utils.dataframe_utils import format_mcap

def test_format_mcap_none():
    assert format_mcap(None, "USD") == "- USD"
    assert format_mcap(float('nan'), "EUR") == "- EUR"
    assert format_mcap(1000000, "USD") == "1,000,000 USD"

def test_normalize_insider_trade_acquisition_mapping():
    raw = {
        "symbol": "AAPL",
        "acquisitionOrDisposition": "A",
        "securitiesTransacted": "100",
        "price": "150.0"
    }
    normalized = normalize_insider_trade(raw)
    assert normalized["acquisition_or_disposition"] == "A"

def test_import_service_profile_mapping():
    # Mock profile from FMP
    profile = {
        "symbol": "AAPL",
        "mktCap": 2500000000000.5,
        "price": 150.5,
        "isEtf": True,
        "fullTimeEmployees": "100000"
    }
    fetched_at = datetime.now(timezone.utc)
    # ImportService._normalize_company_profile is static
    normalized = ImportService._normalize_company_profile(
        profile,
        trade={"company_key": "CIK:1", "company_cik": "1", "symbol": "AAPL", "first_seen_at": fetched_at},
        fetched_at=fetched_at,
    )
    
    assert normalized["current_symbol"] == "AAPL"
    assert normalized["market_cap"] == 2500000000000
    assert isinstance(normalized["market_cap"], int)
    assert normalized["is_etf"] is True
    assert normalized["full_time_employees"] == "100000"

def test_dashboard_gate_pass_kpi():
    # Mock repo with some trades (Dashboard nutzt fetch_trades_enriched_with_company)
    class MockRepo:
        def fetch_trades_enriched_with_company(self, limit=2000, filters=None):
            return pd.DataFrame([
                {"gate_status": "PASS", "transaction_type": "Buy", "sector": "Tech",
                 "filing_date": "2024-01-01", "profile_status": "FETCHED", "company_key": "CIK:1"},
                {"gate_status": "FAIL", "transaction_type": "Sale", "sector": "Health",
                 "filing_date": "2024-01-02", "profile_status": "NOT_REQUESTED", "company_key": "CIK:2"},
                {"gate_status": "PASS", "transaction_type": "Buy", "sector": "Tech",
                 "filing_date": "2024-01-03", "profile_status": "FETCHED", "company_key": "CIK:1"},
                {"gate_status": "PENDING", "transaction_type": "Sale", "sector": "Energy",
                 "filing_date": "2024-01-04", "profile_status": "NOT_REQUESTED", "company_key": "CIK:3"}
            ])
        def count_all(self):
            return 4
        def get_extreme_dates(self):
            return {"min_date": "2024-01-01", "max_date": "2024-01-04"}

    class MockRawRepo:
        def count_all(self):
            return 10

    service = DashboardService(
        raw_repo=MockRawRepo(),
        company_mongo_repo=None,
        trade_repo=MockRepo(),
        company_repo=MockRepo()
    )
    
    payload = service.build_dashboard_payload()
    # P0.4: aktueller Key ist gate_passed_count (nicht gate_pass_records)
    assert payload["gate_passed_count"] == 2


def test_dashboard_sector_normalization_to_unknown():
    class MockRepo:
        def fetch_trades_enriched_with_company(self, limit=2000, filters=None):
            return pd.DataFrame(
                [
                    {"gate_status": "PASS", "transaction_type": "Buy", "sector": None, "filing_date": "2024-01-01",
                     "profile_status": "FETCHED", "company_key": "CIK:1"},
                    {"gate_status": "PASS", "transaction_type": "Buy", "sector": "", "filing_date": "2024-01-02",
                     "profile_status": "FETCHED", "company_key": "CIK:1"},
                    {"gate_status": "PASS", "transaction_type": "Buy", "sector": "   ", "filing_date": "2024-01-03",
                     "profile_status": "FETCHED", "company_key": "CIK:1"},
                ]
            )

        def count_all(self):
            return 3

        def get_extreme_dates(self):
            return {"min_date": "2024-01-01", "max_date": "2024-01-03"}

    service = DashboardService(
        raw_repo=None,
        company_mongo_repo=None,
        trade_repo=MockRepo(),
        company_repo=MockRepo(),
    )
    payload = service.build_dashboard_payload()
    # P0.4: aktueller Key ist sector_distribution_buy / sector_distribution_sell
    # (nicht sector_distribution). Beide müssen vorhanden sein.
    assert "sector_distribution_buy" in payload, "sector_distribution_buy fehlt im Payload"
    assert "sector_distribution_sell" in payload, "sector_distribution_sell fehlt im Payload"

    # Alle Sektoren in beiden Charts müssen "Unknown" enthalten (weil alle Sektoren leer/None sind)
    for key in ("sector_distribution_buy", "sector_distribution_sell"):
        df_chart = payload[key]
        if not df_chart.empty:
            sectors = set(df_chart["sector"].astype(str).tolist())
            assert "None" not in sectors, f"'None'-String darf nicht im {key} vorkommen"

