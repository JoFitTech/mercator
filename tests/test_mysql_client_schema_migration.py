"""Tests fuer die idempotente MySQL-Schema-Nachruestung von insider_trades."""

from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from typing import cast

from src.db.mysql_client import INSIDER_TRADES_MIGRATION_COLUMNS, MySqlClient
from src.db.repositories.trade_repository import InsiderTradeRepository
from src.db.schema import MYSQL_SCHEMA_STATEMENTS


@dataclass(frozen=True)
class _DummySettings:
    name: str = "local"
    host: str = "localhost"
    port: int = 3306
    database: str = "mercator"
    user: str = "root"
    password: str = "pw"
    connect_timeout: int = 5
    create_database: bool = False
    ssl_disabled: bool = True

    def mysql_connection_kwargs(self, include_database: bool = True) -> dict[str, Any]:
        return {}


class _FakeCursor:
    def __init__(self) -> None:
        self.executed_sql: list[str] = []

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        # Parameterwerte sind fuer diese Migrations-Tests nicht relevant.
        self.executed_sql.append(sql)


class _FakeConnection:
    def __init__(self) -> None:
        self.cursor_obj = _FakeCursor()
        self.committed = False

    def cursor(self) -> _FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed = True


class _InspectableMySqlClient(MySqlClient):
    def __init__(self, missing_columns: set[tuple[str, str]]) -> None:
        super().__init__(cast(Any, _DummySettings()))
        self._missing_columns = set(missing_columns)
        self.fake_conn = _FakeConnection()

    @contextmanager
    def connection(self, include_database: bool = True):
        yield self.fake_conn

    def _column_exists(self, cursor, table: str, column: str) -> bool:
        return (table, column) not in self._missing_columns

    def _index_exists(self, cursor, table: str, index_name: str) -> bool:
        return True

    def _constraint_exists(self, cursor, table: str, constraint: str) -> bool:
        return True

    def _has_primary_key(self, cursor, table: str) -> bool:
        return True

    def _query_has_row(self, cursor, query: str, params: tuple | None = None) -> bool:
        return True


def _extract_insider_trades_schema_columns() -> set[str]:
    ddl_blob = "\n".join(MYSQL_SCHEMA_STATEMENTS)
    match = re.search(r"CREATE TABLE IF NOT EXISTS insider_trades\s*\((.*?)\)\s*ENGINE=InnoDB", ddl_blob, re.S)
    assert match is not None

    columns: set[str] = set()
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip().rstrip(",")
        if not line:
            continue
        if line.startswith(("PRIMARY KEY", "UNIQUE KEY", "INDEX", "CONSTRAINT", "FOREIGN KEY")):
            continue
        columns.add(line.split()[0])
    return columns


def test_initialize_schema_backfills_normalized_instrument_type_for_existing_db() -> None:
    client = _InspectableMySqlClient(missing_columns={("insider_trades", "normalized_instrument_type")})

    actions = client.initialize_schema()

    assert "insider_trades: Added `normalized_instrument_type`." in actions
    assert any(
        "ALTER TABLE insider_trades ADD COLUMN normalized_instrument_type VARCHAR(64) NULL" in sql
        for sql in client.fake_conn.cursor_obj.executed_sql
    )
    assert client.fake_conn.committed is True


def test_insider_trades_migration_columns_cover_schema_except_auto_id() -> None:
    schema_columns = _extract_insider_trades_schema_columns()
    migration_columns = {name for name, _definition in INSIDER_TRADES_MIGRATION_COLUMNS}

    assert "id" in schema_columns
    assert "id" not in migration_columns

    missing = sorted((schema_columns - {"id"}) - migration_columns)
    assert missing == []


def test_insider_trade_upsert_fields_are_migration_covered() -> None:
    repo = InsiderTradeRepository(client=None)  # type: ignore[arg-type]
    migration_columns = {name for name, _definition in INSIDER_TRADES_MIGRATION_COLUMNS}

    missing_upsert_columns = sorted(set(repo._upsert_fields) - migration_columns)
    assert missing_upsert_columns == []

