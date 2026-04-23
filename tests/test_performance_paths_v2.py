from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd

from src.db.mysql_client import MySqlClient
from src.db.repositories.company_repository import CompanyRepository
from src.services.dashboard_service import DashboardService
from src.services.historical_market_data_service import HistoricalMarketDataService
from src.services.import_service import ImportService
import src.services.import_service as import_service_module


def test_mysql_client_reuses_connection_pool() -> None:
    settings = MagicMock()
    settings.name = "local"
    settings.mysql_connection_kwargs.return_value = {"host": "localhost"}
    client = MySqlClient(settings)
    pool = MagicMock()
    pool.get_connection.return_value = MagicMock()
    client._pool_by_scope[True] = pool  # type: ignore[attr-defined]

    with client.connection():
        pass
    with client.connection():
        pass

    assert pool.get_connection.call_count == 2


def test_company_trade_stats_uses_recompute_path() -> None:
    service = ImportService.__new__(ImportService)
    repo = MagicMock()
    service.company_mysql_repo = repo
    trades = [
        {"company_key": "SYM:A", "acquisition_or_disposition": "A", "transaction_date": date(2026, 1, 1)},
        {"company_key": "SYM:A", "acquisition_or_disposition": "D", "transaction_date": date(2026, 1, 2)},
    ]

    ImportService._update_company_trade_stats(service, trades)

    repo.recompute_trade_stats_for_company_keys.assert_called_once_with(["SYM:A"])
    repo.upsert_trade_stats_deltas.assert_not_called()


def test_company_repository_page_uses_stats_table() -> None:
    client = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    cursor.description = []
    conn.cursor.return_value.__enter__.return_value = cursor
    client.get_connection.return_value.__enter__.return_value = conn
    repo = CompanyRepository(client)

    repo.list_active_companies_page(limit=10, offset=0)

    executed_sql = cursor.execute.call_args[0][0].lower()
    assert "company_trade_stats" in executed_sql


def test_api3_cache_hit_skips_fmp_call() -> None:
    cache_repo = MagicMock()
    cache_repo.get_symbol_cache.return_value = {
        "avg_20d_volume": 1.0,
        "avg_20d_dollar_volume": 2.0,
        "sma_50": 3.0,
        "sma_200": 4.0,
        "momentum_3m": 0.1,
        "momentum_6m": 0.2,
        "technical_state": "MIXED",
        "liquidity_state": "LOW",
        "to_date": date(2026, 1, 1),
        "refreshed_at": datetime.now(UTC),
    }
    fmp = MagicMock()
    service = HistoricalMarketDataService(fmp, cache_repo=cache_repo)

    signal = service.load_signal("AAPL", today=date(2026, 1, 1))

    assert signal.technical_state == "MIXED"
    fmp.fetch_historical_price_eod_full.assert_not_called()


def test_api3_cache_miss_calls_fmp_and_writes_cache() -> None:
    cache_repo = MagicMock()
    cache_repo.get_symbol_cache.return_value = None
    fmp = MagicMock()
    fmp.fetch_historical_price_eod_full.return_value = [{"date": "2026-01-01", "close": 10.0, "volume": 1000}]
    service = HistoricalMarketDataService(fmp, cache_repo=cache_repo)

    _ = service.load_signal("AAPL", today=date(2026, 1, 1))

    fmp.fetch_historical_price_eod_full.assert_called_once()
    cache_repo.upsert_symbol_cache.assert_called_once()
    payload = cache_repo.upsert_symbol_cache.call_args[0][0]
    assert payload["lookback_from"] == date(2026, 1, 1) - timedelta(days=service.LOOKBACK_DAYS)
    assert payload["lookback_to"] == date(2026, 1, 1)


def test_dashboard_uses_aggregate_repository_path() -> None:
    trade_repo = MagicMock()
    trade_repo.get_max_updated_at.return_value = "2026-01-01"
    trade_repo.fetch_dashboard_kpi_snapshot.return_value = {
        "buy_count": 1,
        "sell_count": 0,
        "buy_volume": 20.0,
        "sell_volume": 0.0,
        "relevant_trades": 1,
        "affected_companies": 1,
        "gate_passed_count": 1,
        "avg_score": 80.0,
    }
    trade_repo.fetch_dashboard_sector_distribution.return_value = pd.DataFrame(
        [{"direction": "BUY", "sector": "Tech", "count": 1, "volume": 20.0}]
    )
    trade_repo.fetch_dashboard_top_trades.side_effect = [
        pd.DataFrame([{"trade_date": "2026-01-01", "accumulated_trade_value_estimated": 20.0}]),
        pd.DataFrame(columns=["trade_date", "accumulated_trade_value_estimated"]),
    ]
    trade_repo.fetch_dashboard_market_cap_distribution.return_value = pd.DataFrame(
        [{"bucket": "Small Cap (<2B)", "companies": 1}]
    )
    company_repo = MagicMock()
    company_repo.get_max_updated_at.return_value = "2026-01-01"
    service = DashboardService(None, None, trade_repo, company_repo)

    payload = service.build_dashboard_payload(filters={})

    assert payload["kpi_relevant_trades_count"] == 1
    trade_repo.fetch_dashboard_kpi_snapshot.assert_called_once()
    trade_repo.fetch_dashboard_market_cap_distribution.assert_called_once()
    trade_repo.fetch_trades_enriched_with_company.assert_not_called()


def test_import_company_persistence_prefers_batch_upsert_many() -> None:
    service = ImportService.__new__(ImportService)
    service.company_mongo_repo = MagicMock()
    service.company_mysql_repo = MagicMock()
    companies = [{"company_key": "SYM:A"}, {"company_key": "SYM:B"}]

    ImportService._persist_company_batch(service, companies)

    service.company_mongo_repo.upsert_profiles.assert_called_once_with(companies)
    service.company_mysql_repo.upsert_companies.assert_called_once_with(companies)


def test_import_uses_api2_bulk_cache_lookup(monkeypatch) -> None:
    monkeypatch.setattr(import_service_module, "normalize_insider_trade", lambda item, fetched_at: dict(item))

    fmp_client = MagicMock()
    fmp_client.fetch_latest_insider_trades.return_value = [
        {
            "company_key": "SYM:AAPL",
            "symbol": "AAPL",
            "acquisition_or_disposition": "A",
            "price": 10.0,
            "qty": 2.0,
            "transaction_date": date(2026, 1, 1),
            "dedupe_key": "AAPL-1",
        }
    ]
    fmp_client.config.profile_ttl_days = 7

    gate_evaluator = MagicMock()
    gate_evaluator.evaluate.return_value = SimpleNamespace(status="PASS", reason="ok")

    raw_repo = MagicMock()
    raw_repo.upsert_raw_trades.return_value = 1

    company_mongo_repo = MagicMock()
    company_mongo_repo.get_recent_profiles_bulk.return_value = {
        "SYM:AAPL": {
            "company_key": "SYM:AAPL",
            "sector": "Technology",
            "market_cap": 100,
            "profile_status": "FETCHED",
            "profile_updated_at": datetime.now(UTC),
        }
    }

    trade_repo = MagicMock()
    company_repo = MagicMock()
    company_repo.recompute_trade_stats_for_company_keys.return_value = 1

    service = ImportService(
        fmp_client=fmp_client,
        gate_evaluator=gate_evaluator,
        raw_repo=raw_repo,
        company_mongo_repo=company_mongo_repo,
        trade_mysql_repo=trade_repo,
        company_mysql_repo=company_repo,
    )

    service.run_hourly_import(page=0, limit=1)

    company_mongo_repo.get_recent_profiles_bulk.assert_called_once()
    company_mongo_repo.get_recent_profile.assert_not_called()

