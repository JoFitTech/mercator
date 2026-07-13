from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.db.repositories.data_quality_repository import DataQualityRepository
from src.db.repositories.import_run_repository import ImportRunRepository
from src.models.stock import ImportRunSummary
from src.models.watchlist import DataQualityIssue


def _build_mysql_mock() -> tuple[MagicMock, MagicMock, MagicMock]:
    client = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    client.get_connection.return_value.__enter__.return_value = conn
    client.get_connection.return_value.__exit__.return_value = False
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.cursor.return_value.__exit__.return_value = False
    return client, conn, cursor


def test_import_run_repository_upserts_and_reads_runs() -> None:
    client, _conn, cursor = _build_mysql_mock()
    repo = ImportRunRepository(client)

    run_id = repo.upsert_run(
        ImportRunSummary(
            import_run_id="run-1",
            provider="fmp",
            import_type="watchlist",
            started_at=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
            status="partial",
            symbols_requested=3,
            symbols_succeeded=2,
            symbols_failed=1,
            raw_responses_written=3,
            clean_records_written=2,
        )
    )

    assert run_id == "run-1"
    sql, params = cursor.execute.call_args[0]
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert params["status"] == "PARTIAL"

    cursor.description = [
        ("import_run_id",),
        ("provider",),
        ("import_type",),
        ("started_at",),
        ("completed_at",),
        ("status",),
    ]
    cursor.fetchone.return_value = ("run-1", "fmp", "watchlist", datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc), None, "PARTIAL")

    loaded = repo.get_run("run-1")

    assert loaded is not None
    assert loaded["import_run_id"] == "run-1"
    assert loaded["status"] == "PARTIAL"


def test_import_run_repository_lists_and_counts_runs_with_filters() -> None:
    client, _conn, cursor = _build_mysql_mock()
    repo = ImportRunRepository(client)

    cursor.description = [
        ("import_run_id",),
        ("provider",),
        ("import_type",),
        ("status",),
    ]
    cursor.fetchall.return_value = [
        ("run-2", "fmp", "watchlist", "SUCCESS"),
        ("run-1", "fmp", "watchlist", "PARTIAL"),
    ]

    rows = repo.list_runs(provider="fmp", import_type="watchlist", status="success", limit=10, offset=0)

    assert [row["import_run_id"] for row in rows] == ["run-2", "run-1"]
    sql, params = cursor.execute.call_args[0]
    assert "provider = %(provider)s" in sql
    assert "UPPER(status) = %(status)s" in sql
    assert params["status"] == "SUCCESS"

    cursor.fetchone.return_value = (2,)
    count = repo.count_runs(provider="fmp", import_type="watchlist", status="success")

    assert count == 2


def test_data_quality_repository_creates_lists_and_resolves_issues() -> None:
    client, _conn, cursor = _build_mysql_mock()
    repo = DataQualityRepository(client)

    cursor.lastrowid = 17
    issue_id = repo.create_issue(
        DataQualityIssue(
            symbol="aapl",
            data_category="company_profile",
            severity="warning",
            status="open",
            message="Profile data is stale",
            detected_at=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
        )
    )

    assert issue_id == 17
    sql, params = cursor.execute.call_args[0]
    assert "INSERT INTO data_quality_issues" in sql
    assert params["symbol"] == "AAPL"
    assert params["status"] == "OPEN"

    cursor.description = [
        ("issue_id",),
        ("symbol",),
        ("data_category",),
        ("status",),
    ]
    cursor.fetchall.return_value = [
        (17, "AAPL", "company_profile", "OPEN"),
    ]
    rows = repo.list_issues(symbol="AAPL", unresolved_only=True, limit=5, offset=0)
    assert rows[0]["issue_id"] == 17

    resolved_at = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
    resolved_issue_id = repo.resolve_issue(17, resolved_at=resolved_at)

    assert resolved_issue_id == 17
    sql, params = cursor.execute.call_args[0]
    assert "SET status = 'RESOLVED'" in sql
    assert params["issue_id"] == 17


def test_data_quality_repository_upserts_existing_issue_by_id() -> None:
    client, _conn, cursor = _build_mysql_mock()
    repo = DataQualityRepository(client)

    cursor.lastrowid = 33
    issue_id = repo.upsert_issue(
        {
            "symbol": "MSFT",
            "data_category": "historical_price",
            "severity": "warning",
            "status": "open",
            "message": "Price data is missing",
            "detected_at": datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
        }
    )

    assert issue_id == 33

