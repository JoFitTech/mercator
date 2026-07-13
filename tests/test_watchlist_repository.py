from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.db.repositories.watchlist_repository import WatchlistRepository
from src.models.watchlist import WatchlistItem


def _build_mysql_mock() -> tuple[MagicMock, MagicMock, MagicMock]:
    client = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    client.get_connection.return_value.__enter__.return_value = conn
    client.get_connection.return_value.__exit__.return_value = False
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.cursor.return_value.__exit__.return_value = False
    return client, conn, cursor


def test_watchlist_repository_upserts_and_fetches_items() -> None:
    client, _conn, cursor = _build_mysql_mock()
    repo = WatchlistRepository(client)

    repo.upsert_item(
        WatchlistItem(
            symbol="aapl",
            display_name="Apple Inc.",
            notes="Core position",
            priority=7,
            active=True,
            resolution_status="unresolved",
        )
    )

    sql, params = cursor.execute.call_args[0]
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert params["symbol"] == "AAPL"
    assert params["resolution_status"] == "UNRESOLVED"

    cursor.description = [
        ("id",),
        ("symbol",),
        ("display_name",),
        ("notes",),
        ("priority",),
        ("active",),
        ("resolution_status",),
        ("created_at",),
        ("updated_at",),
    ]
    cursor.fetchone.return_value = (
        1,
        "AAPL",
        "Apple Inc.",
        "Core position",
        7,
        1,
        "UNRESOLVED",
        datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
    )

    loaded = repo.get_item("aapl")

    assert loaded is not None
    assert loaded["symbol"] == "AAPL"
    assert loaded["resolution_status"] == "UNRESOLVED"


def test_watchlist_repository_lists_unresolved_and_deletes_items() -> None:
    client, _conn, cursor = _build_mysql_mock()
    repo = WatchlistRepository(client)

    cursor.description = [("symbol",), ("resolution_status",)]
    cursor.fetchall.return_value = [("AAPL", "UNRESOLVED")]

    rows = repo.list_unresolved_items(active_only=True)

    assert rows == [{"symbol": "AAPL", "resolution_status": "UNRESOLVED"}]
    sql, _params = cursor.execute.call_args[0]
    assert "resolution_status" in sql.lower()
    assert "active = 1" in sql.lower()

    repo.delete_item("aapl")
    sql, params = cursor.execute.call_args[0]
    assert sql.startswith("DELETE FROM watchlist_items")
    assert params == ("AAPL",)

