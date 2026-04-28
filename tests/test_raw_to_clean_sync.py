from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from src.preprocessing.gate_evaluator import GateEvaluator
from src.services.import_service import ImportService


@dataclass
class _Decision:
    status: str
    reason: str = "ok"


class _RawRepoStub:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def upsert_raw_trades(self, trades: list[dict[str, Any]]) -> int:
        return len(trades)

    def list_latest_raw_trades(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(self.rows)[: int(limit)]


class _CompanyMongoRepoStub:
    def upsert_profile(self, profile: dict[str, Any]) -> None:
        return None


class _TradeRepoStub:
    def __init__(self) -> None:
        self.last_batch: list[dict[str, Any]] = []
        self.upsert_calls = 0
        self.bump_calls = 0

    def upsert_trades(self, trades: list[dict[str, Any]]) -> int:
        self.upsert_calls += 1
        self.last_batch = [dict(t) for t in trades]
        return len(trades)

    def bump_dashboard_state(self) -> None:
        self.bump_calls += 1


class _CompanyMySqlRepoStub:
    def __init__(self, companies_by_key: dict[str, dict[str, Any]] | None = None) -> None:
        self.companies_by_key = companies_by_key or {}
        self.recompute_calls = 0

    def get_companies_by_keys(self, keys: list[str]) -> dict[str, dict[str, Any]]:
        return {key: self.companies_by_key[key] for key in keys if key in self.companies_by_key}

    def upsert_company(self, company: dict[str, Any]) -> None:  # noqa: ARG002
        return None

    def upsert_companies(self, companies: list[dict[str, Any]]) -> None:  # noqa: ARG002
        return None

    def recompute_trade_stats_for_company_keys(self, keys: list[str]) -> None:  # noqa: ARG002
        self.recompute_calls += 1


class _FmpNoCallStub:
    def __init__(self) -> None:
        self.config = SimpleNamespace(profile_ttl_days=7)

    def __getattr__(self, name: str):
        raise AssertionError(f"FMP call is not allowed in Raw->Clean sync: {name}")


class _ScoringServiceStub:
    def compute_trade_score(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "score": 82.0,
            "score_class": "B",
            "core_insider_score": 80.0,
            "investability_score": 78.0,
            "execution_score": 85.0,
            "trade_republic_score": 70.0,
            "final_score": 82.0,
            "final_class": "B",
            "decision_status": "BUY_CANDIDATE",
            "filing_age_days": item.get("filing_age_days"),
        }


class _FmpImportStub:
    def __init__(self) -> None:
        self.config = SimpleNamespace(profile_ttl_days=7)

    def fetch_latest_insider_trades(self, page: int = 0, limit: int = 100):  # noqa: ARG002
        return [
            {
                "symbol": "AAPL",
                "reportingName": "Jane Insider",
                "transactionDate": "2026-01-08",
                "filingDate": "2026-01-10",
                "securitiesTransacted": 100,
                "price": 1200.0,
                "transactionType": "P-Purchase",
                "acquisitionOrDisposition": "A",
                "formType": "4",
                "securityName": "Apple Common Stock",
            },
            {
                "symbol": "MSFT",
                "reportingName": "John Insider",
                "transactionDate": "2026-01-07",
                "filingDate": "2026-01-10",
                "securitiesTransacted": 50,
                "price": 0,
                "transactionType": "P-Purchase",
                "acquisitionOrDisposition": "A",
                "formType": "4",
                "securityName": "Microsoft Common Stock",
            },
        ]


class _GateEvaluatorAlwaysPass:
    def evaluate(self, _item: dict[str, Any]) -> _Decision:
        return _Decision(status="PASS")


def _valid_sync_row(*, dedupe_key: str = "k1", symbol: str = "AAPL", price: float = 1200.0) -> dict[str, Any]:
    return {
        "dedupe_key": dedupe_key,
        "symbol": symbol,
        "symbol_at_trade": symbol,
        "company_key": f"SYM:{symbol}",
        "filing_date": "2026-01-10",
        "transaction_date": "2026-01-08",
        "qty": 100,
        "price": price,
        "form_type": "4",
        "transaction_type": "P-Purchase",
        "acquisition_or_disposition": "A",
        "security_name": "Common Stock",
        "normalized_instrument_type": "STOCK",
        "trade_value_estimated": None,
        "trade_value": None,
        "validation_status": "VALID",
    }


def _build_sync_service(raw_rows: list[dict[str, Any]]) -> tuple[ImportService, _TradeRepoStub]:
    trade_repo = _TradeRepoStub()
    service = ImportService(
        fmp_client=_FmpNoCallStub(),
        gate_evaluator=GateEvaluator(),
        raw_repo=_RawRepoStub(raw_rows),
        company_mongo_repo=_CompanyMongoRepoStub(),
        trade_mysql_repo=trade_repo,
        company_mysql_repo=_CompanyMySqlRepoStub(),
        allow_write=True,
        scoring_service=_ScoringServiceStub(),
    )
    return service, trade_repo


def test_raw_to_clean_sync_skips_missing_dedupe() -> None:
    service, trade_repo = _build_sync_service([_valid_sync_row(dedupe_key="")])

    summary = service.sync_raw_to_clean(limit=10)

    assert summary.raw_candidates == 1
    assert summary.clean_upserted == 0
    assert summary.skipped_missing_dedupe == 1
    assert trade_repo.upsert_calls == 0


def test_raw_to_clean_sync_skips_price_invalid() -> None:
    service, trade_repo = _build_sync_service([_valid_sync_row(price=0.0)])

    summary = service.sync_raw_to_clean(limit=10)

    assert summary.clean_upserted == 0
    assert summary.skipped_validation_failed == 1
    assert trade_repo.upsert_calls == 0


def test_raw_to_clean_sync_skips_missing_symbol() -> None:
    row = _valid_sync_row(symbol="")
    row["symbol"] = ""
    row["symbol_at_trade"] = ""
    service, trade_repo = _build_sync_service([row])

    summary = service.sync_raw_to_clean(limit=10)

    assert summary.clean_upserted == 0
    assert summary.skipped_validation_failed == 1
    assert trade_repo.upsert_calls == 0


def test_raw_to_clean_sync_upserts_valid_clean_trade() -> None:
    service, trade_repo = _build_sync_service([_valid_sync_row(dedupe_key="valid-1", symbol="AAPL", price=1250.0)])

    summary = service.sync_raw_to_clean(limit=10)

    assert summary.clean_upserted == 1
    assert trade_repo.upsert_calls == 1
    assert len(trade_repo.last_batch) == 1
    upserted = trade_repo.last_batch[0]
    assert upserted.get("gate_status") in {"PASS", "PENDING", "PRE_GATE_FAIL", "FAIL"}
    assert upserted.get("validation_status") == "VALID"
    assert upserted.get("score") is not None
    assert upserted.get("score_class") in {"A", "B", "C", "D", "E"}
    assert str(upserted.get("processing_status") or "").upper() != "VALIDATION_FAILED"


def test_raw_to_clean_sync_does_not_call_fmp() -> None:
    service, trade_repo = _build_sync_service([_valid_sync_row(dedupe_key="valid-2", symbol="TSLA", price=1300.0)])

    summary = service.sync_raw_to_clean(limit=10)

    assert summary.clean_upserted == 1
    assert trade_repo.upsert_calls == 1


def test_run_hourly_import_still_filters_validation_failed() -> None:
    trade_repo = _TradeRepoStub()
    service = ImportService(
        fmp_client=_FmpImportStub(),
        gate_evaluator=GateEvaluator(),
        raw_repo=_RawRepoStub([]),
        company_mongo_repo=_CompanyMongoRepoStub(),
        trade_mysql_repo=trade_repo,
        company_mysql_repo=_CompanyMySqlRepoStub(),
        allow_write=True,
        api2_firing_mode="DISABLED",
        scoring_service=_ScoringServiceStub(),
    )

    summary = service.run_hourly_import(limit=10)

    assert summary.fetched_feed_records == 2
    assert summary.upserted_clean_records == 1
    assert len(trade_repo.last_batch) == 1
    assert trade_repo.last_batch[0].get("symbol") == "AAPL"


