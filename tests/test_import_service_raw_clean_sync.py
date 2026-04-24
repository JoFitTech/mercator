from __future__ import annotations

from dataclasses import dataclass

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
            {"dedupe_key": "k1", "symbol_at_trade": "AAPL"},
            {"dedupe_key": "", "symbol_at_trade": "MSFT"},
            {"dedupe_key": "k2", "symbol_at_trade": "TSLA"},
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

