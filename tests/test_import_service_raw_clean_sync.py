from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from src.preprocessing.gate_evaluator import GateEvaluator
from src.services.import_service import ImportService


@dataclass
class _Decision:
    status: str
    reason: str = "ok"


class _GateEvaluatorStub:
    def evaluate(self, _item: dict) -> _Decision:
        return _Decision(status="PASS")


class _RawRepoStub:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def upsert_raw_trades(self, trades: list[dict]) -> int:
        return len(trades)

    def list_latest_raw_trades(self, limit: int = 100) -> list[dict]:
        return list(self.rows)[: int(limit)]


class _CompanyMongoRepoStub:
    def upsert_profile(self, profile: dict) -> None:
        return None


class _TradeRepoStub:
    def __init__(self) -> None:
        self.upsert_calls = 0
        self.last_batch: list[dict] = []
        self.bump_calls = 0

    def upsert_trades(self, trades: list[dict]) -> int:
        self.upsert_calls += 1
        self.last_batch = list(trades)
        return len(trades)

    def bump_dashboard_state(self) -> None:
        self.bump_calls += 1


class _FmpStub:
    pass


class _FmpImportStub:
    def __init__(self) -> None:
        self.config = SimpleNamespace(profile_ttl_days=7)

    def fetch_latest_insider_trades(self, page=0, limit=100):
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


class _RawCaptureRepo:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.saved_batches: list[list[dict]] = []

    def upsert_raw_trades(self, trades: list[dict]) -> int:
        if self.fail:
            raise RuntimeError("mongo unavailable")
        self.saved_batches.append([dict(t) for t in trades])
        return len(trades) - 1  # simuliere 1 Duplikat


def _build_service(raw_rows: list[dict], allow_write: bool = True) -> tuple[ImportService, _TradeRepoStub]:
    trade_repo = _TradeRepoStub()
    service = ImportService(
        fmp_client=_FmpStub(),
        gate_evaluator=_GateEvaluatorStub(),
        raw_repo=_RawRepoStub(raw_rows),
        company_mongo_repo=_CompanyMongoRepoStub(),
        trade_mysql_repo=trade_repo,
        company_mysql_repo=None,
        allow_write=allow_write,
    )
    return service, trade_repo


def test_sync_raw_to_clean_upserts_latest_rows_and_skips_missing_dedupe() -> None:
    service, trade_repo = _build_service(
        [
            {
                "dedupe_key": "k1",
                "symbol": "AAPL",
                "symbol_at_trade": "AAPL",
                "filing_date": "2026-01-10",
                "transaction_date": "2026-01-08",
                "qty": 100,
                "price": 1200,
                "form_type": "4",
                "transaction_type": "P-Purchase",
                "acquisition_or_disposition": "A",
                "security_name": "Common Stock",
                "normalized_instrument_type": "STOCK",
                "trade_value_estimated": 120000,
                "trade_value": 120000,
            },
            {"dedupe_key": "", "symbol_at_trade": "MSFT"},
            {
                "dedupe_key": "k2",
                "symbol": "TSLA",
                "symbol_at_trade": "TSLA",
                "filing_date": "2026-01-10",
                "transaction_date": "2026-01-08",
                "qty": 100,
                "price": 1500,
                "form_type": "4",
                "transaction_type": "P-Purchase",
                "acquisition_or_disposition": "A",
                "security_name": "Common Stock",
                "normalized_instrument_type": "STOCK",
                "trade_value_estimated": 150000,
                "trade_value": 150000,
            },
        ]
    )

    summary = service.sync_raw_to_clean(limit=10)

    assert summary.raw_candidates == 3
    assert summary.clean_upserted == 2
    assert summary.skipped_missing_dedupe == 1
    assert trade_repo.upsert_calls == 1
    assert trade_repo.bump_calls == 1
    assert [row.get("dedupe_key") for row in trade_repo.last_batch] == ["k1", "k2"]


def test_sync_raw_to_clean_returns_zero_summary_when_no_raw_rows() -> None:
    service, trade_repo = _build_service([])

    summary = service.sync_raw_to_clean(limit=50)

    assert summary.raw_candidates == 0
    assert summary.clean_upserted == 0
    assert summary.skipped_missing_dedupe == 0
    assert trade_repo.upsert_calls == 0


def test_sync_raw_to_clean_raises_when_write_is_disabled() -> None:
    service, _trade_repo = _build_service([{"dedupe_key": "k1"}], allow_write=False)

    try:
        service.sync_raw_to_clean(limit=5)
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "deaktiviert" in str(exc)

    assert raised is True


def test_run_hourly_import_saves_raw_with_metadata_and_duplicate_counter() -> None:
    raw_repo = _RawCaptureRepo(fail=False)
    trade_repo = _TradeRepoStub()
    service = ImportService(
        fmp_client=_FmpImportStub(),
        gate_evaluator=_GateEvaluatorStub(),
        raw_repo=raw_repo,
        company_mongo_repo=_CompanyMongoRepoStub(),
        trade_mysql_repo=trade_repo,
        company_mysql_repo=None,
        allow_write=True,
    )

    summary = service.run_hourly_import(limit=10)

    assert summary.fetched_feed_records == 2
    assert summary.inserted_raw_records == 1
    assert summary.skipped_raw_duplicates == 1
    assert summary.raw_storage_error is None
    assert len(raw_repo.saved_batches) == 1
    saved = raw_repo.saved_batches[0]
    assert len(saved) == 2
    assert all(row.get("source") == "fmp" for row in saved)
    assert all(row.get("source_endpoint") == "/stable/insider-trading/latest" for row in saved)
    assert all(row.get("import_run_id") for row in saved)
    assert all(row.get("imported_at") is not None for row in saved)
    assert all("raw_payload" in row for row in saved)


def test_run_hourly_import_reports_raw_storage_error_when_mongo_fails() -> None:
    raw_repo = _RawCaptureRepo(fail=True)
    trade_repo = _TradeRepoStub()
    service = ImportService(
        fmp_client=_FmpImportStub(),
        gate_evaluator=_GateEvaluatorStub(),
        raw_repo=raw_repo,
        company_mongo_repo=_CompanyMongoRepoStub(),
        trade_mysql_repo=trade_repo,
        company_mysql_repo=None,
        allow_write=True,
    )

    summary = service.run_hourly_import(limit=10)

    assert summary.fetched_feed_records == 2
    assert summary.inserted_raw_records == 0
    assert summary.raw_storage_error is not None
    assert "mongo" in summary.raw_storage_error.lower()


def test_run_hourly_import_excludes_price_invalid_from_clean_mysql_upsert() -> None:
    raw_repo = _RawCaptureRepo(fail=False)
    trade_repo = _TradeRepoStub()
    service = ImportService(
        fmp_client=_FmpImportStub(),
        gate_evaluator=GateEvaluator(),
        raw_repo=raw_repo,
        company_mongo_repo=_CompanyMongoRepoStub(),
        trade_mysql_repo=trade_repo,
        company_mysql_repo=None,
        allow_write=True,
        api2_firing_mode="DISABLED",
    )

    summary = service.run_hourly_import(limit=10)

    assert summary.fetched_feed_records == 2
    assert summary.upserted_clean_records == 1
    assert len(trade_repo.last_batch) == 1
    assert trade_repo.last_batch[0].get("symbol") == "AAPL"


