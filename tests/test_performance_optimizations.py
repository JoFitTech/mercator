from __future__ import annotations

import pandas as pd

from src.db.repositories.trade_repository import InsiderTradeRepository
from src.db.repositories.company_repository import CompanyRepository
from src.services.dashboard_service import DashboardService
from src.services.import_service import ImportService


class _DummyClient:
    def __init__(self) -> None:
        self.execute_many_calls: list[tuple[str, list[dict]]] = []

    def execute_many(self, sql: str, params_seq: list[dict], *, commit: bool = True) -> int:
        self.execute_many_calls.append((sql, params_seq))
        return len(params_seq)


class _TradeRepoForDashboard:
    def __init__(self) -> None:
        self.fetch_calls = 0
        self.state_calls = 0

    def get_max_updated_at(self):
        self.state_calls += 1
        return "2026-01-01 00:00:00"

    def fetch_trades_enriched_with_company(self, limit: int, filters: dict | None = None):
        self.fetch_calls += 1
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


class _CompanyRepoForDashboard:
    def __init__(self) -> None:
        self.state_calls = 0

    def get_max_updated_at(self):
        self.state_calls += 1
        return "2026-01-01 00:00:00"


class _RawRepoStub:
    def upsert_raw_trades(self, trades: list[dict]) -> int:
        return len(trades)


class _TradeMysqlRepoStub:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def upsert_trades(self, rows: list[dict]) -> int:
        self.rows.extend(rows)
        return len(rows)


class _CompanyMongoRepoStub:
    def get_recent_profile(self, company_key: str, ttl_days: int):
        return None

    def upsert_profile(self, profile: dict) -> None:
        return None


class _CompanyMysqlRepoStub:
    def upsert_companies(self, companies: list[dict]) -> int:
        return len(companies)

    def get_companies_by_keys(self, company_keys: list[str]) -> dict[str, dict]:
        return {}


class _Gate:
    class _Decision:
        status = "PASS"
        reason = "ok"

    def evaluate(self, item: dict):
        return self._Decision()


class _Scoring:
    def compute_trade_score(self, item: dict) -> dict:
        return {"score": 60, "score_class": "B"}


class _Enrichment:
    def enrich_company_profile(self, symbol: str):
        raise RuntimeError("enrichment unavailable")


def test_trade_upsert_trades_uses_executemany_batch() -> None:
    client = _DummyClient()
    repo = InsiderTradeRepository(client)  # type: ignore[arg-type]

    written = repo.upsert_trades([
        {"company_key": "SYM:A", "symbol_at_trade": "A", "dedupe_key": "a", "fetched_at": "2026-01-01"},
        {"company_key": "SYM:B", "symbol_at_trade": "B", "dedupe_key": "b", "fetched_at": "2026-01-01"},
    ])

    assert written == 2
    assert len(client.execute_many_calls) == 1
    assert len(client.execute_many_calls[0][1]) == 2


def test_company_upsert_companies_uses_executemany_batch() -> None:
    client = _DummyClient()
    repo = CompanyRepository(client)  # type: ignore[arg-type]

    written = repo.upsert_companies([
        {"company_key": "SYM:A", "current_symbol": "A"},
        {"company_key": "SYM:B", "current_symbol": "B"},
    ])

    assert written == 2
    assert len(client.execute_many_calls) == 1


def test_dashboard_payload_uses_short_cache() -> None:
    trade_repo = _TradeRepoForDashboard()
    company_repo = _CompanyRepoForDashboard()
    service = DashboardService(
        raw_repo=None,
        company_mongo_repo=None,
        trade_repo=trade_repo,  # type: ignore[arg-type]
        company_repo=company_repo,  # type: ignore[arg-type]
    )

    payload_a = service.build_dashboard_payload(filters={"symbol": "AAPL"})
    payload_b = service.build_dashboard_payload(filters={"symbol": "AAPL"})

    assert payload_a["kpi_relevant_trades_count"] >= 0
    assert payload_b["kpi_relevant_trades_count"] >= 0
    assert trade_repo.fetch_calls == 1
    assert trade_repo.state_calls <= 2
    assert company_repo.state_calls <= 2


def test_import_persists_trades_even_if_enrichment_fails(monkeypatch) -> None:
    monkeypatch.setattr("src.services.import_service.normalize_insider_trade", lambda item, fetched_at: item)

    fmp_client = type(
        "Fmp",
        (),
        {
            "config": type("Cfg", (), {"profile_ttl_days": 30})(),
            "fetch_latest_insider_trades": staticmethod(lambda page, limit: [{"symbol": "A", "company_key": "SYM:A", "price": 5, "qty": 1, "acquisition_or_disposition": "A"}]),
        },
    )()

    trade_repo = _TradeMysqlRepoStub()
    service = ImportService(
        fmp_client=fmp_client,
        gate_evaluator=_Gate(),
        raw_repo=_RawRepoStub(),
        company_mongo_repo=_CompanyMongoRepoStub(),
        trade_mysql_repo=trade_repo,  # type: ignore[arg-type]
        company_mysql_repo=_CompanyMysqlRepoStub(),  # type: ignore[arg-type]
        api2_firing_mode="ALL TRADED COMPANIES",
        tr_ingestion_service=None,
        tr_matching_service=None,
        enrichment_service=_Enrichment(),
        scoring_service=_Scoring(),
    )

    summary = service.run_hourly_import()

    assert summary.upserted_clean_records == 1
    assert len(trade_repo.rows) == 1
