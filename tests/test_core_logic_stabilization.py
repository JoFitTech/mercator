import pytest
import pandas as pd
from datetime import datetime, timezone
from src.preprocessing.cleaning import normalize_insider_trade
from src.models.company import Company
from src.services.company_enrichment_service import CompanyEnrichmentService
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


def test_import_service_profile_mapping_accepts_market_cap_alias():
    fetched_at = datetime.now(timezone.utc)
    normalized = ImportService._normalize_company_profile(
        {"symbol": "AAPL", "marketCap": 2500000000000},
        trade={"company_key": "CIK:1", "company_cik": "1", "symbol": "AAPL", "first_seen_at": fetched_at},
        fetched_at=fetched_at,
    )

    assert normalized["market_cap"] == 2500000000000


def test_company_enrichment_uses_market_cap_alias_from_fmp():
    service = CompanyEnrichmentService(fmp_client=None)  # type: ignore[arg-type]
    company = Company(symbol="AAPL")

    service._apply_fmp_data(
        company,
        {
            "companyName": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "marketCap": 3200000000000,
        },
    )

    assert company.market_cap == 3200000000000
    assert company.sector == "Technology"
    assert company.sector_resolution_status == "RESOLVED"

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


def test_dashboard_accepts_score_alias_from_repository():
    """Dashboard muss mit `score` arbeiten, auch wenn `score_value` fehlt."""
    class MockRepo:
        def fetch_trades_enriched_with_company(self, limit=2000, filters=None):
            return pd.DataFrame([
                {
                    "gate_status": "PASS",
                    "sector": "Tech",
                    "transaction_date": "2024-01-01",
                    "profile_status": "FETCHED",
                    "company_key": "CIK:1",
                    "price": 10.0,
                    "qty": 10,
                    "trade_value_estimated": 100.0,
                    "acquisition_or_disposition": "A",
                    "score": 80.0,
                    "dashboard_valid": True,
                }
            ])

        def get_extreme_dates(self):
            return {"min_date": "2024-01-01", "max_date": "2024-01-01"}

    service = DashboardService(
        raw_repo=None,
        company_mongo_repo=None,
        trade_repo=MockRepo(),
        company_repo=MockRepo(),
    )
    payload = service.build_dashboard_payload()
    assert payload["avg_score"] == 80.0


def test_dashboard_uses_mongo_profile_when_mysql_join_is_missing():
    class MockRepo:
        def fetch_trades_enriched_with_company(self, limit=2000, filters=None):
            return pd.DataFrame([
                {
                    "gate_status": "PASS",
                    "symbol": "AAPL",
                    "transaction_date": "2024-01-01",
                    "profile_status": "NOT_REQUESTED",
                    "company_key": "CIK:1",
                    "price": 10.0,
                    "qty": 10,
                    "trade_value_estimated": 100.0,
                    "acquisition_or_disposition": "A",
                    "market_cap": None,
                    "sector": None,
                }
            ])

    class MockCompanyMongoRepo:
        def get_profiles_bulk(self, company_keys):
            result = {}
            for company_key in company_keys:
                if company_key == "CIK:1":
                    result[company_key] = {
                        "company_key": "CIK:1",
                        "profile_status": "FETCHED",
                        "sector": "Technology",
                        "marketCap": 1500000000,
                    }
            return result

    service = DashboardService(
        raw_repo=None,
        company_mongo_repo=MockCompanyMongoRepo(),
        trade_repo=MockRepo(),
        company_repo=MockRepo(),
    )

    payload = service.build_dashboard_payload()

    assert not payload["sector_distribution_buy"].empty
    assert payload["sector_distribution_buy"].iloc[0]["sector"] == "Technology"
    assert payload["market_cap_distribution"].set_index("bucket").loc["Small Cap (<2B)", "companies"] == 1


def test_dashboard_uses_aliased_company_join_columns_without_crash():
    class MockRepo:
        def fetch_dashboard_kpi_snapshot(self, filters=None):
            return {
                "relevant_trades": 1,
                "affected_companies": 1,
                "buy_count": 1,
                "sell_count": 0,
                "buy_volume": 100.0,
                "sell_volume": 0.0,
                "gate_passed_count": 1,
                "avg_score": 80.0,
            }

        def fetch_dashboard_sector_distribution(self, filters=None):
            return pd.DataFrame(
                [{"direction": "BUY", "sector": "Technology", "count": 1, "volume": 100.0}]
            )

        def fetch_dashboard_market_cap_distribution(self, filters=None):
            return pd.DataFrame(
                [{"bucket": "Small Cap (<2B)", "companies": 1}]
            )

        def fetch_trades_enriched_with_company(self, limit=2000, filters=None):
            return pd.DataFrame(
                [
                    {
                        "gate_status": "PASS",
                        "symbol_at_trade": "AAPL",
                        "transaction_date": "2024-01-01",
                        "profile_status": "FETCHED",
                        "company_key": "CIK:1",
                        "price": 10.0,
                        "qty": 10,
                        "trade_value_estimated": 100.0,
                        "acquisition_or_disposition": "A",
                        "market_cap": None,
                        "company_market_cap": 1500000000,
                        "sector": None,
                        "company_sector": "Technology",
                        "score": 80.0,
                    }
                ]
            )

        def get_dashboard_state_token(self):
            return "t1"

    service = DashboardService(
        raw_repo=None,
        company_mongo_repo=None,
        trade_repo=MockRepo(),
        company_repo=MockRepo(),
    )

    payload = service.build_dashboard_payload()

    assert payload["payload_error_message"] is None
    assert payload["sector_distribution_buy"].iloc[0]["sector"] == "Technology"
    assert payload["market_cap_distribution"].set_index("bucket").loc["Small Cap (<2B)", "companies"] == 1


