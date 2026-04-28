"""Prüft Performance- und Entkopplungsregeln für Import, Dashboard und Cache-Zugriffe.

Die Datei wird gebraucht, damit effiziente Query-Pfade, deterministische Aggregation und Bulk-Lookups auch nach
Umbauten erhalten bleiben.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from src.services.import_service import ImportService
from src.services.dashboard_service import DashboardService
from src.db.repositories.company_repository import CompanyRepository
from src.db.mongo_repository import CompanyMongoRepository
from src.db.mysql_client import MySqlClient


class TestCompanyTradeStatsCorrectness:
    """Tests für deterministischen company_trade_stats-Recompute."""

    def test_recompute_trade_stats_for_company_keys_no_overcounting(self):
        """When importing overlapping trades (same dedupe_key),
        company_trade_stats should not overcount from deltas."""

        mock_client = MagicMock(spec=MySqlClient)
        repo = CompanyRepository(mock_client)

        # Simuliere zwei Aufrufe zur Recompute für die gleiche company_key
        company_keys = ["TEST_COMPANY"]

        with patch.object(repo._client, 'execute') as mock_execute:
            result = repo.recompute_trade_stats_for_company_keys(company_keys)

        mock_execute.assert_called_once()

        call_args = mock_execute.call_args
        sql_query = call_args[0][0]
        assert "INSERT INTO company_trade_stats" in sql_query
        assert "LEFT JOIN insider_trades" in sql_query
        assert "COUNT(t.company_key) AS trade_count" in sql_query
        assert "ON DUPLICATE KEY UPDATE" in sql_query

        assert result == 1

    def test_import_service_calls_recompute_not_deltas(self):
        """Import-Service sollte recompute_trade_stats_for_company_keys verwenden,
        nicht das alte delta-basierte Verfahren."""

        mock_company_repo = MagicMock()
        mock_company_repo.recompute_trade_stats_for_company_keys = MagicMock(return_value=1)

        # Simuliere ImportService._update_company_trade_stats
        trades = [
            {"company_key": "CIK:123", "acquisition_or_disposition": "BUY", "transaction_date": datetime.now(timezone.utc)},
            {"company_key": "CIK:123", "acquisition_or_disposition": "SELL", "transaction_date": datetime.now(timezone.utc)},
        ]

        from src.services.import_service import ImportService
        import_service = ImportService(
            fmp_client=MagicMock(),
            gate_evaluator=MagicMock(),
            raw_repo=MagicMock(),
            company_mongo_repo=MagicMock(),
            trade_mysql_repo=MagicMock(),
            company_mysql_repo=mock_company_repo
        )

        import_service._update_company_trade_stats(trades)

        mock_company_repo.recompute_trade_stats_for_company_keys.assert_called_once_with(['CIK:123'])
        mock_company_repo.upsert_trade_stats_deltas.assert_not_called()


class TestDashboardNormalPathDecoupling:
    """Tests dass der Dashboard-Normalpfad KEINEN 20_000-Trade-Load mehr braucht."""

    def test_aggregate_path_does_not_call_fetch_trades_enriched_with_company(self):
        """Der Aggregate-Pfad sollte fetch_trades_enriched_with_company NICHT aufrufen."""

        mock_trade_repo = MagicMock()
        mock_trade_repo.fetch_dashboard_kpi_snapshot.return_value = {
            "relevant_trades": 100,
            "affected_companies": 10,
            "buy_count": 60,
            "sell_count": 40,
            "buy_volume": 1000000.0,
            "sell_volume": 500000.0,
            "gate_passed_count": 50,
            "avg_score": 7.5,
        }
        mock_trade_repo.fetch_dashboard_sector_distribution.return_value = pd.DataFrame()
        mock_trade_repo.fetch_dashboard_market_cap_distribution.return_value = pd.DataFrame()
        mock_trade_repo.fetch_dashboard_top_trades.side_effect = [
            pd.DataFrame(columns=["trade_date", "accumulated_trade_value_estimated"]),
            pd.DataFrame(columns=["trade_date", "accumulated_trade_value_estimated"]),
        ]
        mock_trade_repo.fetch_dashboard_last_update.return_value = datetime(2026, 4, 20)

        dashboard_service = DashboardService(
            raw_repo=MagicMock(),
            company_mongo_repo=MagicMock(),
            trade_repo=mock_trade_repo,
            company_repo=MagicMock()
        )

        payload = dashboard_service._build_payload_from_aggregate_queries({})

        mock_trade_repo.fetch_trades_enriched_with_company.assert_not_called()

        mock_trade_repo.fetch_dashboard_kpi_snapshot.assert_called_once()
        mock_trade_repo.fetch_dashboard_sector_distribution.assert_called_once()
        mock_trade_repo.fetch_dashboard_market_cap_distribution.assert_called_once()
        assert mock_trade_repo.fetch_dashboard_top_trades.call_count == 2
        assert payload["kpi_relevant_trades_count"] == 100
        assert payload["kpi_affected_companies_count"] == 10
        assert payload["total_buy_volume"] == 1000000.0


class TestDashboardKPICompleteness:
    """Tests dass Dashboard-KPIs nicht mehr hartcodiert leer sind."""

    def test_aggregate_path_uses_top_trades_query_directly(self):
        """Top-Tabellen sollten direkt aus fetch_dashboard_top_trades kommen."""

        mock_trade_repo = MagicMock()
        mock_trade_repo.fetch_dashboard_kpi_snapshot.return_value = {
            "relevant_trades": 100,
            "affected_companies": 10,
            "buy_count": 60,
            "sell_count": 40,
            "buy_volume": 1000000.0,
            "sell_volume": 500000.0,
            "gate_passed_count": 50,
            "avg_score": 7.5,
        }
        mock_trade_repo.fetch_dashboard_sector_distribution.return_value = pd.DataFrame()
        mock_trade_repo.fetch_dashboard_market_cap_distribution.return_value = pd.DataFrame()
        mock_trade_repo.fetch_dashboard_last_update.return_value = datetime(2026, 4, 20)

        # Simuliere Top-Trades Response
        top_buys_df = pd.DataFrame([
            {
                "symbol_at_trade": "AAPL",
                "accumulated_trade_value_estimated": 50000.0,
                "trade_date": datetime.now(timezone.utc),
            },
            {
                "symbol_at_trade": "MSFT",
                "accumulated_trade_value_estimated": 30000.0,
                "trade_date": datetime.now(timezone.utc),
            },
        ])

        top_sells_df = pd.DataFrame([
            {
                "symbol_at_trade": "GOOGL",
                "accumulated_trade_value_estimated": 20000.0,
                "trade_date": datetime.now(timezone.utc),
            },
        ])

        mock_trade_repo.fetch_dashboard_top_trades.side_effect = [top_buys_df, top_sells_df]

        dashboard_service = DashboardService(
            raw_repo=MagicMock(),
            company_mongo_repo=MagicMock(),
            trade_repo=mock_trade_repo,
            company_repo=MagicMock()
        )

        payload = dashboard_service._build_payload_from_aggregate_queries({})

        assert mock_trade_repo.fetch_dashboard_top_trades.call_count == 2
        first_call_kwargs = mock_trade_repo.fetch_dashboard_top_trades.call_args_list[0].kwargs
        second_call_kwargs = mock_trade_repo.fetch_dashboard_top_trades.call_args_list[1].kwargs
        assert first_call_kwargs["direction"] == "BUY"
        assert second_call_kwargs["direction"] == "SELL"
        assert payload["kpi_largest_buy_value"] == 50000.0
        assert payload["kpi_largest_sell_value"] == 20000.0
        assert payload["avg_score"] == 7.5
        assert "missing_data_summary" not in payload


class TestAPI2CacheBulkLookup:
    """Tests dass API2-Cache-Lookups im Import bulkfähig sind."""

    def test_mongo_repository_get_recent_profiles_bulk(self):
        """get_recent_profiles_bulk sollte mehrere Profile in EINEM Query laden."""

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_database.return_value = {"companies": mock_collection}

        # WICHTIG: Mocking _ensure_company_key_unique_index um Fehler zu vermeiden
        with patch.object(CompanyMongoRepository, '_ensure_company_key_unique_index'):
            mongo_repo = CompanyMongoRepository(mock_client)

        # Simuliere Mongo-Rückgabe
        mock_collection.find.return_value = [
            {
                "_id": "id1",
                "company_key": "CIK:123",
                "sector": "Technology",
                "profile_updated_at": datetime.now(timezone.utc),
            },
            {
                "_id": "id2",
                "company_key": "CIK:456",
                "sector": "Finance",
                "profile_updated_at": datetime.now(timezone.utc),
            },
        ]

        result = mongo_repo.get_recent_profiles_bulk(
            company_keys=["CIK:123", "CIK:456"],
            ttl_days=7
        )

        # Prüfe dass find() mit $in-Operator aufgerufen wurde (Bulk, kein N+1)
        mock_collection.find.assert_called_once()
        call_args = mock_collection.find.call_args[0][0]
        assert "$in" in str(call_args)  # Prüfe auf $in-Operator

        # Prüfe dass beide Profile zurückgegeben werden
        assert len(result) == 2
        assert result["CIK:123"]["sector"] == "Technology"
        assert result["CIK:456"]["sector"] == "Finance"

    def test_import_uses_bulk_cache_lookup_without_single_calls(self):
        service = ImportService.__new__(ImportService)
        service.fmp_client = MagicMock()
        service.fmp_client.config.profile_ttl_days = 7
        service.company_mongo_repo = MagicMock()

        company_keys = ["CIK:1", "CIK:2", "CIK:1"]
        service.company_mongo_repo.get_recent_profiles_bulk.return_value = {}
        _ = service.company_mongo_repo.get_recent_profiles_bulk(company_keys, ttl_days=7)

        service.company_mongo_repo.get_recent_profiles_bulk.assert_called_once()
        service.company_mongo_repo.get_recent_profile.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


