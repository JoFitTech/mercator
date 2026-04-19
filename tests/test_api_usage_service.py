from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from mysql.connector import errorcode
from mysql.connector.errors import ProgrammingError

from src.db.repositories.api_usage_repository import ApiUsageRepository
from src.services.api_usage_service import ApiUsageService


def test_api_usage_repository_reads_primary_table_name() -> None:
    mock_client = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.fetchone.return_value = (date(2026, 4, 19), "fmp", 3, 250, None)
    mock_cursor.description = [
        ("day_key",),
        ("provider",),
        ("call_count",),
        ("limit_count",),
        ("last_request_at",),
    ]

    mock_client.get_connection.return_value.__enter__.return_value = mock_conn
    mock_client.get_connection.return_value.__exit__.return_value = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    repo = ApiUsageRepository(mock_client)
    usage = repo.get_usage(date(2026, 4, 19), "fmp")

    assert usage is not None
    executed_query = mock_cursor.execute.call_args[0][0]
    assert "FROM app_api_usage" in executed_query


def test_api_usage_repository_falls_back_to_legacy_table_when_primary_missing() -> None:
    mock_client = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    missing_table_exc = ProgrammingError(msg="Table 'mercator.app_api_usage' doesn't exist", errno=errorcode.ER_NO_SUCH_TABLE)
    mock_cursor.execute.side_effect = [
        missing_table_exc,
        None,
    ]
    mock_cursor.fetchone.return_value = None

    mock_client.get_connection.return_value.__enter__.return_value = mock_conn
    mock_client.get_connection.return_value.__exit__.return_value = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    repo = ApiUsageRepository(mock_client)
    usage = repo.get_usage(date(2026, 4, 19), "fmp")

    assert usage is None
    assert mock_cursor.execute.call_count == 2
    first_query = mock_cursor.execute.call_args_list[0][0][0]
    second_query = mock_cursor.execute.call_args_list[1][0][0]
    assert "FROM app_api_usage" in first_query
    assert "FROM api_usage" in second_query


def test_api_usage_service_returns_default_on_repository_error() -> None:
    class _RepoError:
        def get_usage(self, _day, _provider):
            raise RuntimeError("db not ready")

    service = ApiUsageService(repository=_RepoError())  # type: ignore[arg-type]
    usage = service.get_current_usage("fmp")

    assert usage["provider"] == "fmp"
    assert usage["call_count"] == 0
    assert usage["limit_count"] == 250
    assert usage["remaining"] == 250


def test_api_usage_service_computes_remaining_when_usage_exists() -> None:
    class _RepoOk:
        def get_usage(self, _day, _provider):
            return {
                "day_key": date.today(),
                "provider": "fmp",
                "call_count": 7,
                "limit_count": 10,
                "last_request_at": None,
            }

    service = ApiUsageService(repository=_RepoOk())  # type: ignore[arg-type]
    usage = service.get_current_usage("fmp")

    assert usage["remaining"] == 3

