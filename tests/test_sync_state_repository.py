from __future__ import annotations

from unittest.mock import MagicMock

from mysql.connector import errorcode
from mysql.connector.errors import ProgrammingError

from src.db.repositories.sync_state_repository import SyncStateRepository


def test_load_initializes_schema_when_sync_state_table_missing() -> None:
    mock_client = MagicMock()
    first_conn = MagicMock()
    second_conn = MagicMock()
    create_conn = MagicMock()
    final_conn = MagicMock()
    first_cursor = MagicMock()
    second_cursor = MagicMock()
    create_cursor = MagicMock()
    final_cursor = MagicMock()

    missing_table_exc = ProgrammingError(msg="Table 'mercator.app_sync_state' doesn't exist", errno=errorcode.ER_NO_SUCH_TABLE)
    first_cursor.execute.side_effect = missing_table_exc
    second_cursor.fetchone.return_value = None
    create_cursor.execute.return_value = None
    final_cursor.fetchone.return_value = {
        "state_key": "startup_mysql_sync",
        "pending_uni_sync": False,
        "sync_in_progress": False,
    }

    first_conn.cursor.return_value.__enter__.return_value = first_cursor
    first_conn.cursor.return_value.__exit__.return_value = False
    second_conn.cursor.return_value.__enter__.return_value = second_cursor
    second_conn.cursor.return_value.__exit__.return_value = False
    create_conn.cursor.return_value.__enter__.return_value = create_cursor
    create_conn.cursor.return_value.__exit__.return_value = False
    final_conn.cursor.return_value.__enter__.return_value = final_cursor
    final_conn.cursor.return_value.__exit__.return_value = False

    mock_client.connection.return_value.__enter__.side_effect = [first_conn, second_conn, create_conn, final_conn]
    mock_client.connection.return_value.__exit__.return_value = False

    repo = SyncStateRepository(mock_client)
    state = repo.load()

    assert state.state_key == repo.STATE_KEY
    assert state.pending_uni_sync is False
    mock_client.initialize_schema.assert_called_once()
