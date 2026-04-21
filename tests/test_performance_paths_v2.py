from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock

import pandas as pd

from src.db.mysql_client import MySqlClient
from src.db.repositories.company_repository import CompanyRepository
from src.services.dashboard_service import DashboardService
from src.services.historical_market_data_service import HistoricalMarketDataService
from src.services.import_service import ImportService


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


def test_company_trade_stats_delta_update_called() -> None:
    service = ImportService.__new__(ImportService)
    repo = MagicMock()
    service.company_mysql_repo = repo
    trades = [
        {"company_key": "SYM:A", "acquisition_or_disposition": "A", "transaction_date": date(2026, 1, 1)},
        {"company_key": "SYM:A", "acquisition_or_disposition": "D", "transaction_date": date(2026, 1, 2)},
    ]

    ImportService._update_company_trade_stats(service, trades)

    rows = repo.upsert_trade_stats_deltas.call_args[0][0]
    assert rows[0]["trade_count_delta"] == 2
    assert rows[0]["buy_count_delta"] == 1
    assert rows[0]["sell_count_delta"] == 1


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
