"""Tests für fetch_trades-Filterlogik im InsiderTradeRepository (P0.1 + P0.2)."""

from __future__ import annotations

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch, call

from src.db.repositories.trade_repository import InsiderTradeRepository


# ---------------------------------------------------------------------------
# Hilfsfunktion: Erstellt ein Mock-MySqlClient-Objekt, das pd.read_sql kapselt
# ---------------------------------------------------------------------------

def _make_repo_with_df(df: pd.DataFrame) -> tuple[InsiderTradeRepository, list]:
    """Gibt (repo, captured_calls) zurück.

    captured_calls sammelt alle (sql, params) Argumente, mit denen pd.read_sql
    aufgerufen wurde.
    """
    mock_client = MagicMock()
    mock_conn = MagicMock()
    mock_client.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_client.get_connection.return_value.__exit__ = MagicMock(return_value=False)
    repo = InsiderTradeRepository(mock_client)
    return repo, mock_client, mock_conn


class TestFetchTradesSymbolFilter:
    """P0.2: symbol-Filter muss auf symbol_at_trade laufen, NICHT auf company_key."""

    def test_symbol_filter_uses_symbol_at_trade(self):
        mock_client = MagicMock()
        mock_conn = MagicMock()
        mock_client.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_client.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        repo = InsiderTradeRepository(mock_client)

        captured = {}

        def fake_read_sql(sql, conn, params):
            captured["sql"] = sql
            captured["params"] = params
            return pd.DataFrame()

        with patch("src.db.repositories.trade_repository.pd.read_sql", side_effect=fake_read_sql):
            repo.fetch_trades(filters={"symbol": "AAPL"})

        assert "symbol_at_trade LIKE %s" in captured["sql"], (
            "Symbolfilter muss auf symbol_at_trade LIKE laufen, nicht auf company_key"
        )
        assert "company_key" not in captured["sql"] or "company_key = %s" not in captured["sql"].replace("LEFT", "")

    def test_company_key_filter_is_separate_from_symbol(self):
        """company_key-Filter (interner Schlüssel) ist separat vom UI-Symbolfilter."""
        mock_client = MagicMock()
        mock_conn = MagicMock()
        mock_client.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_client.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        repo = InsiderTradeRepository(mock_client)

        captured = {}

        def fake_read_sql(sql, conn, params):
            captured["sql"] = sql
            captured["params"] = params
            return pd.DataFrame()

        with patch("src.db.repositories.trade_repository.pd.read_sql", side_effect=fake_read_sql):
            repo.fetch_trades(filters={"company_key": "CIK:123"})

        assert "company_key = %s" in captured["sql"]
        assert "symbol_at_trade" not in captured["sql"]


class TestFetchTradesAllFilters:
    """P0.1: Alle UI-Filter müssen tatsächlich in SQL landen."""

    def _run(self, filters: dict) -> dict:
        mock_client = MagicMock()
        mock_conn = MagicMock()
        mock_client.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_client.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        repo = InsiderTradeRepository(mock_client)

        captured = {}

        def fake_read_sql(sql, conn, params):
            captured["sql"] = sql
            captured["params"] = params
            return pd.DataFrame()

        with patch("src.db.repositories.trade_repository.pd.read_sql", side_effect=fake_read_sql):
            repo.fetch_trades(filters=filters)
        return captured

    def test_gate_status_filter(self):
        c = self._run({"gate_status": "PASS"})
        assert "gate_status = %s" in c["sql"]
        assert "PASS" in c["params"]

    def test_validation_status_filter(self):
        c = self._run({"validation_status": "VALID"})
        assert "validation_status = %s" in c["sql"]

    def test_acquisition_or_disposition_filter(self):
        c = self._run({"acquisition_or_disposition": "A"})
        assert "acquisition_or_disposition = %s" in c["sql"]

    def test_reporting_name_filter(self):
        c = self._run({"reporting_name": "John"})
        assert "reporting_name LIKE %s" in c["sql"]
        assert "%John%" in c["params"]

    def test_min_score_positive(self):
        c = self._run({"min_score": 5})
        assert "score >= %s" in c["sql"]
        assert 5 in c["params"]

    def test_min_score_zero_is_ignored(self):
        c = self._run({"min_score": 0})
        assert "score" not in c["sql"]

    def test_min_value_positive(self):
        c = self._run({"min_value": 100000})
        assert "trade_value_estimated >= %s" in c["sql"]
        assert 100000 in c["params"]

    def test_trade_republic_universe_status_filter(self):
        c = self._run({"trade_republic_universe_status": "IN_UNIVERSE"})
        assert "trade_republic_universe_status = %s" in c["sql"]

    def test_trade_republic_universe_status_all_is_ignored(self):
        c = self._run({"trade_republic_universe_status": "ALL"})
        assert "trade_republic_universe_status = %s" not in c["sql"]

    def test_date_from_and_to(self):
        c = self._run({"date_from": "2024-01-01", "date_to": "2024-12-31"})
        assert "transaction_date >= %s" in c["sql"]
        assert "transaction_date <= %s" in c["sql"]

    def test_no_filters_returns_all(self):
        c = self._run({})
        assert "WHERE" not in c["sql"]

    def test_sql_uses_stable_sort(self):
        """Sortierung muss ORDER BY transaction_date DESC, filing_date DESC enthalten."""
        c = self._run({})
        assert "ORDER BY transaction_date DESC" in c["sql"]
        assert "filing_date DESC" in c["sql"]


def test_fetch_trades_enriched_supports_dedupe_key_filter():
    mock_client = MagicMock()
    mock_conn = MagicMock()
    mock_client.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_client.get_connection.return_value.__exit__ = MagicMock(return_value=False)
    repo = InsiderTradeRepository(mock_client)

    captured = {}

    def fake_read_sql(sql, conn, params):
        captured["sql"] = sql
        captured["params"] = params
        return pd.DataFrame()

    with patch("src.db.repositories.trade_repository.pd.read_sql", side_effect=fake_read_sql):
        repo.fetch_trades_enriched_with_company(filters={"dedupe_key": "abc"}, limit=1)

    assert "t.dedupe_key = %s" in captured["sql"]
    assert "abc" in captured["params"]
    assert "score_value" in captured["sql"]


def test_upsert_trade_sets_trade_republic_defaults() -> None:
    mock_client = MagicMock()
    repo = InsiderTradeRepository(mock_client)

    repo.upsert_trade(
        {
            "company_key": "SYM:ABC",
            "symbol_at_trade": "ABC",
            "dedupe_key": "abc_1",
            "fetched_at": "2026-01-01 00:00:00",
        }
    )

    _, params = mock_client.execute.call_args[0]
    assert params["trade_republic_universe_status"] == "UNKNOWN"
    assert params["trade_republic_match_method"] == "NONE"
    assert params["trade_republic_match_confidence"] == "LOW"


def test_upsert_sql_contains_v2_api3_columns() -> None:
    repo = InsiderTradeRepository(MagicMock())
    sql = repo._upsert_sql
    assert "avg_20d_volume" in sql
    assert "avg_20d_dollar_volume" in sql
    assert "momentum_3m" in sql
    assert "liquidity_state" in sql
