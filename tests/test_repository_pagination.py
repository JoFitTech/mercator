from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from src.db.repositories.trade_repository import InsiderTradeRepository
from src.db.repositories.company_repository import CompanyRepository


def test_trade_repository_fetch_page_applies_limit_offset() -> None:
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
        repo.fetch_trades_page(filters={"symbol": "AAPL"}, limit=50, offset=100)

    assert "LIMIT %s OFFSET %s" in captured["sql"]
    assert captured["params"][-2:] == [50, 100]


def test_company_repository_count_active_companies_with_search() -> None:
    mock_client = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (12,)
    conn.cursor.return_value.__enter__.return_value = cursor
    mock_client.get_connection.return_value.__enter__.return_value = conn
    repo = CompanyRepository(mock_client)

    count = repo.count_active_companies(search_term="AAPL")

    assert count == 12
    args = cursor.execute.call_args[0]
    assert "company_name LIKE %s" in args[0]
