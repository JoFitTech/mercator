"""Reproduzierbare Performance- und Mongo-Diagnostik für Mercator.

Die Messungen sind bewusst synthetisch/isoliert gehalten, um ohne echte DB reproduzierbar zu sein.
"""

from __future__ import annotations

import re
import socket
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from src.config.settings import load_settings
from src.db.mongo_client import MongoClientWrapper
from src.db.repositories.company_repository import CompanyRepository
from src.db.repositories.trade_repository import InsiderTradeRepository
from src.services.dashboard_service import DashboardService
from src.services.historical_market_data_service import HistoricalMarketDataService


@dataclass
class MetricRow:
    area: str
    scenario: str
    duration_ms: float
    rows: int
    cache: str
    sql_queries: int


class _SyntheticMySqlClient:
    def __init__(self, per_query_delay_ms: float = 2.0) -> None:
        self.execute_calls = 0
        self.executemany_calls = 0
        self.sql_queries = 0
        self._delay = per_query_delay_ms / 1000.0

    def execute(self, _sql: str, _params: Any = None, *, commit: bool = True) -> int:
        self.execute_calls += 1
        self.sql_queries += 1
        time.sleep(self._delay)
        return 1

    def execute_many(self, _sql: str, params_seq: list[dict[str, Any]], *, commit: bool = True) -> int:
        self.executemany_calls += 1
        self.sql_queries += 1
        time.sleep(self._delay)
        return len(params_seq)


class _Cursor:
    def __init__(self, parent: "_SyntheticPagedClient") -> None:
        self.parent = parent
        self._result: tuple[int] | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, _sql: str, _params: Any = None) -> None:
        self.parent.sql_queries += 1
        self._result = (self.parent.count_result,)

    def fetchone(self):
        return self._result

    def fetchall(self):
        return []


class _Conn:
    def __init__(self, parent: "_SyntheticPagedClient") -> None:
        self.parent = parent

    def cursor(self):
        return _Cursor(self.parent)


class _SyntheticPagedClient(_SyntheticMySqlClient):
    def __init__(self, count_result: int, page_rows: int) -> None:
        super().__init__()
        self.count_result = count_result
        self.page_rows = page_rows

    @contextmanager
    def get_connection(self):
        yield _Conn(self)


class _DashTradeRepo:
    def __init__(self, delay_ms: float = 12.0) -> None:
        self.fetch_calls = 0
        self.state_calls = 0
        self.sql_queries = 0
        self.delay_s = delay_ms / 1000.0

    def get_max_updated_at(self):
        self.state_calls += 1
        self.sql_queries += 1
        return datetime(2026, 1, 1, 10, 0, 0)

    def fetch_trades_enriched_with_company(self, limit: int, filters: dict | None = None) -> pd.DataFrame:
        self.fetch_calls += 1
        self.sql_queries += 1
        time.sleep(self.delay_s)
        return pd.DataFrame(
            [
                {
                    "symbol_at_trade": "AAPL",
                    "reporting_name": "Insider",
                    "acquisition_or_disposition": "A",
                    "price": 10,
                    "qty": 2,
                    "trade_value_estimated": 20,
                    "transaction_date": "2026-01-01",
                    "profile_status": "FETCHED",
                    "sector": "Technology",
                    "market_cap": 100,
                    "score": 80,
                    "gate_status": "PASS",
                }
            ]
        )

    def fetch_dashboard_kpi_snapshot(self, filters: dict | None = None) -> dict[str, Any]:
        self.sql_queries += 1
        return {"buy_count": 1, "sell_count": 0, "buy_volume": 20.0, "sell_volume": 0.0, "relevant_trades": 1, "affected_companies": 1, "gate_passed_count": 1, "avg_score": 80.0}

    def fetch_dashboard_sector_distribution(self, filters: dict | None = None) -> pd.DataFrame:
        self.sql_queries += 1
        return pd.DataFrame([{"direction": "BUY", "sector": "Technology", "count": 1, "volume": 20.0}])

    def fetch_dashboard_top_trades(self, direction: str, filters: dict | None = None, limit: int = 5) -> pd.DataFrame:
        self.sql_queries += 1
        if direction == "SELL":
            return pd.DataFrame(columns=["trade_date", "accumulated_trade_value_estimated"])
        return pd.DataFrame([{"trade_date": "2026-01-01", "accumulated_trade_value_estimated": 20.0}])


class _DashCompanyRepo:
    def __init__(self) -> None:
        self.state_calls = 0
        self.sql_queries = 0

    def get_max_updated_at(self):
        self.state_calls += 1
        self.sql_queries += 1
        return datetime(2026, 1, 1, 10, 0, 0)


def _trade_payload(symbol: str) -> dict[str, Any]:
    return {
        "company_key": f"SYM:{symbol}",
        "symbol_at_trade": symbol,
        "dedupe_key": f"{symbol}-1",
        "fetched_at": "2026-01-01 00:00:00",
    }


def benchmark_import_batch_vs_legacy() -> tuple[MetricRow, MetricRow]:
    trades = [_trade_payload(f"S{i}") for i in range(100)]

    legacy_client = _SyntheticMySqlClient()
    legacy_repo = InsiderTradeRepository(legacy_client)  # type: ignore[arg-type]
    t0 = time.perf_counter()
    for trade in trades:
        legacy_repo.upsert_trade(trade)
    legacy_ms = (time.perf_counter() - t0) * 1000

    batch_client = _SyntheticMySqlClient()
    batch_repo = InsiderTradeRepository(batch_client)  # type: ignore[arg-type]
    t1 = time.perf_counter()
    batch_repo.upsert_trades(trades)
    batch_ms = (time.perf_counter() - t1) * 1000

    return (
        MetricRow("Import", "Legacy-loop-simulation", legacy_ms, len(trades), "n/a", legacy_client.sql_queries),
        MetricRow("Import", "Current-batch", batch_ms, len(trades), "n/a", batch_client.sql_queries),
    )


def benchmark_dashboard_cache() -> tuple[MetricRow, MetricRow]:
    trade_repo = _DashTradeRepo()
    company_repo = _DashCompanyRepo()
    service = DashboardService(
        raw_repo=None,
        company_mongo_repo=None,
        trade_repo=trade_repo,  # type: ignore[arg-type]
        company_repo=company_repo,  # type: ignore[arg-type]
    )
    filters = {"symbol": "AAPL"}

    t0 = time.perf_counter()
    payload_a = service.build_dashboard_payload(filters=filters)
    miss_ms = (time.perf_counter() - t0) * 1000
    miss_queries = trade_repo.sql_queries + company_repo.sql_queries

    t1 = time.perf_counter()
    payload_b = service.build_dashboard_payload(filters=filters)
    hit_ms = (time.perf_counter() - t1) * 1000
    total_queries = trade_repo.sql_queries + company_repo.sql_queries

    rows = int(payload_a.get("kpi_relevant_trades_count", 0) or payload_b.get("kpi_relevant_trades_count", 0))
    return (
        MetricRow("Dashboard", "Cache miss (state lookup + aggregation)", miss_ms, rows, "miss", miss_queries),
        MetricRow("Dashboard", "Cache hit (state lookup only)", hit_ms, rows, "hit", total_queries - miss_queries),
    )


def benchmark_trades_page_query_path() -> MetricRow:
    client = _SyntheticPagedClient(count_result=2500, page_rows=100)
    repo = InsiderTradeRepository(client)  # type: ignore[arg-type]

    original_read_sql = pd.read_sql

    def fake_read_sql(_sql, _conn, params=None):
        client.sql_queries += 1
        return pd.DataFrame([_trade_payload("AAPL") for _ in range(client.page_rows)])

    pd.read_sql = fake_read_sql  # type: ignore[assignment]
    try:
        t0 = time.perf_counter()
        count = repo.count_trades(filters={"symbol": "AA"})
        page = repo.fetch_trades_page(filters={"symbol": "AA"}, limit=100, offset=0)
        elapsed_ms = (time.perf_counter() - t0) * 1000
    finally:
        pd.read_sql = original_read_sql  # type: ignore[assignment]

    return MetricRow("Trades page", "count + page", elapsed_ms, min(len(page), count), "n/a", client.sql_queries)


def benchmark_companies_page_query_path() -> MetricRow:
    client = _SyntheticPagedClient(count_result=1800, page_rows=100)
    repo = CompanyRepository(client)  # type: ignore[arg-type]

    def fake_list_active_companies_page(limit: int, offset: int, search_term: str | None = None):
        client.sql_queries += 1
        return [
            {
                "current_symbol": f"S{i}",
                "company_name": f"Company {i}",
                "trade_count": 5,
            }
            for i in range(limit)
        ]

    repo.list_active_companies_page = fake_list_active_companies_page  # type: ignore[assignment]
    t0 = time.perf_counter()
    count = repo.count_active_companies(search_term="A")
    rows = repo.list_active_companies_page(limit=100, offset=0, search_term="A")
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return MetricRow("Companies page", "count + page", elapsed_ms, min(len(rows), count), "n/a", client.sql_queries)


def benchmark_dashboard_aggregate_path() -> MetricRow:
    trade_repo = _DashTradeRepo()
    company_repo = _DashCompanyRepo()
    service = DashboardService(raw_repo=None, company_mongo_repo=None, trade_repo=trade_repo, company_repo=company_repo)  # type: ignore[arg-type]
    t0 = time.perf_counter()
    payload = service.build_dashboard_payload(filters={"symbol": "AAPL"})
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return MetricRow("Dashboard", "Aggregate query path", elapsed_ms, int(payload.get("kpi_relevant_trades_count", 0)), "miss", trade_repo.sql_queries + company_repo.sql_queries)


class _Api3CacheRepo:
    def __init__(self, cached: dict[str, Any] | None) -> None:
        self.cached = cached
        self.writes = 0

    def get_symbol_cache(self, symbol: str) -> dict[str, Any] | None:
        return self.cached

    def upsert_symbol_cache(self, payload: dict[str, Any]) -> None:
        self.writes += 1


def benchmark_api3_cache_hit_miss() -> tuple[MetricRow, MetricRow]:
    fmp_calls = {"count": 0}

    class _Fmp:
        def fetch_historical_price_eod_full(self, symbol: str, date_from: str, date_to: str):
            fmp_calls["count"] += 1
            return [{"date": "2026-01-01", "close": 10, "volume": 1000}]

    miss_service = HistoricalMarketDataService(_Fmp(), cache_repo=_Api3CacheRepo(cached=None))  # type: ignore[arg-type]
    t0 = time.perf_counter()
    _ = miss_service.load_signal("AAPL")
    miss_ms = (time.perf_counter() - t0) * 1000

    cache_row = {
        "symbol": "AAPL",
        "avg_20d_volume": 1000.0,
        "avg_20d_dollar_volume": 10000.0,
        "sma_50": 10.0,
        "sma_200": 10.0,
        "momentum_3m": 0.0,
        "momentum_6m": 0.0,
        "technical_state": "MIXED",
        "liquidity_state": "LOW",
        "to_date": datetime(2026, 1, 2).date(),
        "refreshed_at": datetime.now(),
    }
    hit_service = HistoricalMarketDataService(_Fmp(), cache_repo=_Api3CacheRepo(cached=cache_row))  # type: ignore[arg-type]
    t1 = time.perf_counter()
    _ = hit_service.load_signal("AAPL", today=datetime(2026, 1, 1).date())
    hit_ms = (time.perf_counter() - t1) * 1000
    return (
        MetricRow("API3", "cache miss", miss_ms, 1, "miss", fmp_calls["count"]),
        MetricRow("API3", "cache hit", hit_ms, 1, "hit", fmp_calls["count"] - 1),
    )


def diagnose_mongo() -> dict[str, str]:
    settings = load_settings()
    uri = settings.mongo.uri
    host = "unknown"
    port = "unknown"
    m = re.match(r"^mongodb(?:\+srv)?://(?:[^@/]+@)?([^:/?]+)(?::(\d+))?", uri)
    if m:
        host = m.group(1)
        port = m.group(2) or ("27017" if "+srv" not in uri else "27017")

    tcp_ok = False
    tcp_error = ""
    try:
        with socket.create_connection((host, int(port)), timeout=1.5):
            tcp_ok = True
    except Exception as exc:
        tcp_error = str(exc)

    ping_ok = False
    ping_error = ""
    try:
        db = MongoClientWrapper(settings.mongo, server_selection_timeout_ms=2000).get_database()
        db.command("ping")
        ping_ok = True
    except Exception as exc:
        ping_error = str(exc)

    if ping_ok:
        root_cause = "none"
        category = "healthy"
    elif not tcp_ok:
        root_cause = "MongoDB-Dienst lokal nicht erreichbar"
        category = "runtime_environment_or_missing_service"
    elif "Authentication failed" in ping_error:
        root_cause = "Credentials/Authentifizierung"
        category = "configuration"
    else:
        root_cause = "Unklarer Verbindungsfehler"
        category = "configuration_or_runtime"

    return {
        "mongo_uri": uri,
        "host": host,
        "port": port,
        "tcp_connect": "ok" if tcp_ok else f"fail ({tcp_error})",
        "mongo_ping": "ok" if ping_ok else f"fail ({ping_error})",
        "classification": category,
        "confirmed_root_cause": root_cause,
    }


def _print_metrics(rows: list[MetricRow]) -> None:
    print("| Bereich | Szenario | Dauer (ms) | Zeilen | Cache | SQL Queries |")
    print("|---|---|---:|---:|---|---:|")
    for row in rows:
        print(
            f"| {row.area} | {row.scenario} | {row.duration_ms:.2f} | {row.rows} | {row.cache} | {row.sql_queries} |"
        )


def main() -> None:
    metrics: list[MetricRow] = []
    metrics.extend(benchmark_import_batch_vs_legacy())
    metrics.extend(benchmark_dashboard_cache())
    metrics.append(benchmark_trades_page_query_path())
    metrics.append(benchmark_companies_page_query_path())
    metrics.append(benchmark_dashboard_aggregate_path())
    metrics.extend(benchmark_api3_cache_hit_miss())

    print("# Mercator Performance Diagnostics")
    _print_metrics(metrics)

    mongo_diag = diagnose_mongo()
    print("\n# MongoDB Diagnosis")
    for key, value in mongo_diag.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
