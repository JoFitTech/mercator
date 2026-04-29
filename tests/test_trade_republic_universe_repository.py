from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

from src.db.repositories.trade_republic_universe_repository import TradeRepublicUniverseRepository
from src.domain.trade_republic_universe import TradeRepublicUniverseInstrument


class _CursorStub:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object | None]] = []
        self.executemany_calls: list[tuple[str, list[tuple[object, ...]]]] = []

    def execute(self, sql: str, params=None) -> None:
        self.executed.append((" ".join(sql.split()), params))

    def executemany(self, sql: str, seq) -> None:
        self.executemany_calls.append((" ".join(sql.split()), list(seq)))

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _ConnStub:
    def __init__(self) -> None:
        self.cursor_stub = _CursorStub()
        self.committed = False

    def cursor(self, **_kwargs):
        return self.cursor_stub

    def commit(self) -> None:
        self.committed = True


class _ClientStub:
    def __init__(self) -> None:
        self.conn = _ConnStub()

    @contextmanager
    def connection(self, include_database: bool = True):
        yield self.conn


def test_replace_snapshot_runs_transaction_and_insert() -> None:
    client = _ClientStub()
    repo = TradeRepublicUniverseRepository(client)

    repo.replace_snapshot(
        [
            TradeRepublicUniverseInstrument(
                isin="US0378331005",
                symbol="AAPL",
                instrument_name="Apple Inc.",
                country="US",
                asset_class="STOCK",
            )
        ],
        {
            "source_url": "data/reference/trade_republic/trade_republic_stocks.csv",
            "source_hash": "abc123",
            "source_type": "local_csv",
            "valid_rows": 1,
            "invalid_rows": 0,
            "last_import_status": "SUCCESS",
            "source_last_refreshed_at": datetime(2026, 4, 29, 12, 0, 0),
        },
    )

    executed_sql = [sql for sql, _ in client.conn.cursor_stub.executed]
    assert any("DELETE FROM trade_republic_universe_reference" in sql for sql in executed_sql)
    assert any("INSERT INTO trade_republic_universe_meta" in sql for sql in executed_sql)
    assert client.conn.cursor_stub.executemany_calls
    assert client.conn.committed is True


def test_replace_snapshot_empty_aborts_before_delete() -> None:
    client = _ClientStub()
    repo = TradeRepublicUniverseRepository(client)

    try:
        repo.replace_snapshot([], {"source_url": "x"})
    except ValueError as exc:
        assert "darf nicht leer" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

    executed_sql = [sql for sql, _ in client.conn.cursor_stub.executed]
    assert not any("DELETE FROM trade_republic_universe_reference" in sql for sql in executed_sql)


def test_store_error_updates_meta_without_delete() -> None:
    client = _ClientStub()
    repo = TradeRepublicUniverseRepository(client)

    repo.store_error("data/reference/trade_republic/trade_republic_stocks.csv", "boom")

    executed_sql = [sql for sql, _ in client.conn.cursor_stub.executed]
    assert any("INSERT INTO trade_republic_universe_meta" in sql for sql in executed_sql)
    assert not any("DELETE FROM trade_republic_universe_reference" in sql for sql in executed_sql)
    assert client.conn.committed is True

