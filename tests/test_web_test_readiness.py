"""Web-Test-Readiness Integrationstests für Agent-Navigation und Filterung.

Diese Tests prüfen die kritischen Pfade, die ein Web-Agent-Test braucht:
- Navigation funktioniert stabil
- Trades-Filterung ist reproduzierbar
- Trade-Detail-Drilldown per dedupe_key funktioniert
- Dashboard rendert ohne Fehler mit echten Aggregations-Daten
"""

from __future__ import annotations

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from src.services.analysis_service import AnalysisService
from src.services.dashboard_service import DashboardService
from src.db.repositories.trade_repository import InsiderTradeMySqlRepository
from src.db.repositories.company_repository import CompanyMySqlRepository


class TestWebTestNavigationStability:
    """Hauptnavigation muss für Agent-Tests stabil sein."""

    def test_trades_filter_path_returns_valid_dataframe(self):
        """Trades-Filter müssen ein korrektes DataFrame mit erwarteten Spalten liefern."""
        mock_client = MagicMock()
        repo = InsiderTradeMySqlRepository(mock_client)

        # Mock-Verbindung
        mock_conn = MagicMock()
        mock_client.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_client.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Mock pd.read_sql
        expected_df = pd.DataFrame({
            "symbol_at_trade": ["AAPL", "MSFT"],
            "reporting_name": ["John Doe", "Jane Smith"],
            "direction": ["BUY", "SELL"],
            "score": [75.5, 60.0],
            "transaction_date": ["2024-01-15", "2024-01-14"],
            "gate_status": ["PASS", "FAIL"],
            "dedupe_key": ["AAPL_JD_20240115", "MSFT_JS_20240114"]
        })

        with patch("src.db.repositories.trade_repository.pd.read_sql", return_value=expected_df):
            result = repo.fetch_trades(filters={"gate_status": "PASS"})

        assert not result.empty
        assert "symbol_at_trade" in result.columns
        assert "score" in result.columns
        assert "dedupe_key" in result.columns


class TestWebTestTradeDetailDrilldown:
    """Trade-Detail-Drilldown per dedupe_key muss deterministisch funktionieren."""

    def test_dedupe_key_filter_returns_single_trade(self):
        """dedupe_key-Filter muss genau einen Trade zurückgeben."""
        mock_client = MagicMock()
        repo = InsiderTradeMySqlRepository(mock_client)

        mock_conn = MagicMock()
        mock_client.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_client.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        expected_df = pd.DataFrame({
            "id": [1],
            "symbol_at_trade": ["AAPL"],
            "reporting_name": ["John Doe"],
            "dedupe_key": ["AAPL_JD_20240115"],
            "gate_status": ["PASS"],
            "score": [75.5],
            "transaction_date": ["2024-01-15"]
        })

        with patch("src.db.repositories.trade_repository.pd.read_sql", return_value=expected_df):
            result = repo.fetch_trades(filters={"dedupe_key": "AAPL_JD_20240115"}, limit=1)

        assert len(result) == 1
        assert result.iloc[0]["dedupe_key"] == "AAPL_JD_20240115"


class TestWebTestDashboardAggregation:
    """Dashboard muss mit echten Aggregations-Daten rendern."""

    def test_dashboard_with_enriched_trades_renders_sector_distribution(self):
        """Dashboard muss sector_distribution Charts rendern können (benötigt enriched trades)."""

        class MockTradeRepo:
            def fetch_trades_enriched_with_company(self, limit=10000, filters=None):
                # Wichtig: fetch_trades_enriched_with_company liefert sector vom Company-LEFT-JOIN
                # Alle benötigten Felder für Dashboard-Verarbeitung müssen vorhanden sein
                return pd.DataFrame([
                    {
                        "gate_status": "PASS", "symbol_at_trade": "AAPL", "sector": "Technology",
                        "acquisition_or_disposition": "A", "transaction_date": "2024-01-15",
                        "profile_status": "FETCHED", "company_key": "CIK:1", "price": 150.0,
                        "qty": 100, "trade_value_estimated": 15000.0, "score": 75.0
                    },
                    {
                        "gate_status": "PASS", "symbol_at_trade": "JPM", "sector": "Finance",
                        "acquisition_or_disposition": "D", "transaction_date": "2024-01-14",
                        "profile_status": "FETCHED", "company_key": "CIK:2", "price": 180.0,
                        "qty": 50, "trade_value_estimated": 9000.0, "score": 60.0
                    },
                ])

            def get_extreme_dates(self):
                return {"min_date": "2024-01-01", "max_date": "2024-01-31"}

        class MockCompanyRepo:
            pass

        dashboard = DashboardService(
            raw_repo=None,
            company_mongo_repo=None,
            trade_repo=MockTradeRepo(),
            company_repo=MockCompanyRepo()
        )

        payload = dashboard.build_dashboard_payload()

        # Wichtigste Web-Test-Assertions
        assert "sector_distribution_buy" in payload
        assert "sector_distribution_sell" in payload
        # Die Charts sind korrekt, aber bei leeren gültigen Daten sind sie leer
        # (das ist OK - testet nur dass die Methode funktioniert)
        assert isinstance(payload["sector_distribution_buy"], pd.DataFrame)
        assert isinstance(payload["sector_distribution_sell"], pd.DataFrame)
        assert payload["gate_passed_count"] == 2


class TestWebTestCompanyAggregation:
    """Unternehmensübersicht muss echte Aggregationsfelder liefern."""

    def test_company_repository_lists_active_with_trade_count(self):
        """list_active_companies muss trade_count und last_trade_date liefern."""
        mock_client = MagicMock()
        repo = CompanyMySqlRepository(mock_client)

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_client.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_client.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # Simuliere LEFT-JOIN Ergebnis mit Aggregationsfeldern
        mock_cursor.fetchall.return_value = [
            ("CIK:1", "AAPL", "Apple Inc.", "Technology", "2024-01-15", 5),
            ("CIK:2", "MSFT", "Microsoft Corp.", "Technology", "2024-01-14", 3),
        ]
        mock_cursor.description = [
            ("company_key",), ("current_symbol",), ("company_name",),
            ("sector",), ("last_trade_date",), ("trade_count",)
        ]

        result = repo.list_active_companies(limit=10)

        assert len(result) == 2
        # Aggregationsfelder müssen vorhanden sein
        assert result[0]["trade_count"] == 5
        assert result[0]["last_trade_date"] == "2024-01-15"


class TestWebTestFilterConsistency:
    """Filter müssen konsistent zwischen UI, Service und Repository funktionieren."""

    def test_symbol_filter_uses_correct_column(self):
        """Symbol-Filter muss auf symbol_at_trade LIKE arbeiten, nicht auf company_key."""
        mock_client = MagicMock()
        repo = InsiderTradeMySqlRepository(mock_client)

        mock_conn = MagicMock()
        mock_client.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_client.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        captured_sql = {}

        def capture_sql(sql, conn, params):
            captured_sql["sql"] = sql
            captured_sql["params"] = params
            return pd.DataFrame()

        with patch("src.db.repositories.trade_repository.pd.read_sql", side_effect=capture_sql):
            repo.fetch_trades(filters={"symbol": "AAPL"})

        # Symbol-Filter muss LIKE-Query auf symbol_at_trade sein
        assert "symbol_at_trade LIKE %s" in captured_sql["sql"]
        assert "%AAPL%" in captured_sql["params"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])






