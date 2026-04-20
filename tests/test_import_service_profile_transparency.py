from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from src.services.import_service import ImportService


@dataclass
class _Decision:
    status: str
    reason: str = "ok"


class _GateEvaluatorStub:
    def evaluate(self, _item: dict) -> _Decision:
        return _Decision(status="PASS")


class _RawRepoStub:
    def upsert_raw_trades(self, trades: list[dict]) -> int:
        return len(trades)


class _CompanyMongoRepoStub:
    def __init__(self, cached_company_keys: set[str] | None = None) -> None:
        self.cached_company_keys = cached_company_keys or set()
        self.cache_checks: list[str] = []
        self.upserted_profiles: list[dict] = []

    def get_recent_profile(self, company_key: str, ttl_days: int):
        self.cache_checks.append(f"{company_key}:{ttl_days}")
        if company_key in self.cached_company_keys:
            return {"company_key": company_key}
        return None

    def upsert_profile(self, profile: dict) -> None:
        self.upserted_profiles.append(profile)


@dataclass
class _EnrichedCompany:
    sector_resolution_status: str = "RESOLVED"
    symbol: str | None = None


class _EnrichmentServiceStub:
    def __init__(self, fail_symbols: set[str] | None = None) -> None:
        self.fail_symbols = fail_symbols or set()
        self.calls: list[str] = []

    def enrich_company_profile(self, symbol: str) -> _EnrichedCompany:
        self.calls.append(symbol)
        if symbol in self.fail_symbols:
            raise RuntimeError(f"boom for {symbol}")
        return _EnrichedCompany(sector_resolution_status="RESOLVED", symbol=symbol)


class _ScoringServiceStub:
    def compute_trade_score(self, _trade: dict) -> dict[str, int | str]:
        return {"score": 1, "score_class": "LOW"}


def _build_service(
    *,
    mode: str = "ALL TRADED COMPANIES",
    cached_company_keys: set[str] | None = None,
    fail_symbols: set[str] | None = None,
) -> tuple[ImportService, _EnrichmentServiceStub, _CompanyMongoRepoStub]:
    fmp_client = SimpleNamespace(
        config=SimpleNamespace(profile_ttl_days=30),
        fetch_latest_insider_trades=lambda page, limit: [
            {"symbol": "AAPL", "company_key": "AAPL"},
            {"symbol": "MSFT", "company_key": "MSFT"},
            {"symbol": "AAPL", "company_key": "AAPL"},
        ],
    )
    company_mongo_repo = _CompanyMongoRepoStub(cached_company_keys=cached_company_keys)
    enrichment_service = _EnrichmentServiceStub(fail_symbols=fail_symbols)

    service = ImportService(
        fmp_client=fmp_client,
        gate_evaluator=_GateEvaluatorStub(),
        raw_repo=_RawRepoStub(),
        company_mongo_repo=company_mongo_repo,
        trade_mysql_repo=None,
        company_mysql_repo=None,
        api2_firing_mode=mode,
        tr_ingestion_service=None,
        tr_matching_service=None,
        enrichment_service=enrichment_service,
        scoring_service=_ScoringServiceStub(),
    )
    return service, enrichment_service, company_mongo_repo


def test_all_traded_companies_counts_unique_symbols_as_candidates(monkeypatch) -> None:
    monkeypatch.setattr("src.services.import_service.normalize_insider_trade", lambda item, fetched_at: item)

    service, _enrichment, _repo = _build_service(mode="ALL TRADED COMPANIES")

    summary = service.run_hourly_import()

    assert summary.symbols_considered_for_enrichment == 2


def test_cache_hit_increases_cache_hits_but_not_fetched_profiles(monkeypatch) -> None:
    monkeypatch.setattr("src.services.import_service.normalize_insider_trade", lambda item, fetched_at: item)

    service, enrichment, _repo = _build_service(cached_company_keys={"AAPL", "MSFT"})

    summary = service.run_hourly_import()

    assert summary.profile_cache_hits == 2
    assert summary.fetched_profiles == 0
    assert summary.profile_fetch_attempts == 0
    assert enrichment.calls == []


def test_successful_external_fetch_increases_attempts_and_fetched(monkeypatch) -> None:
    monkeypatch.setattr("src.services.import_service.normalize_insider_trade", lambda item, fetched_at: item)

    service, enrichment, _repo = _build_service(cached_company_keys=set())

    summary = service.run_hourly_import()

    assert summary.profile_fetch_attempts == 2
    assert summary.fetched_profiles == 2
    assert summary.profile_failures == 0
    assert sorted(enrichment.calls) == ["AAPL", "MSFT"]


def test_failed_profile_fetch_increases_failures(monkeypatch) -> None:
    monkeypatch.setattr("src.services.import_service.normalize_insider_trade", lambda item, fetched_at: item)

    service, _enrichment, _repo = _build_service(cached_company_keys=set(), fail_symbols={"MSFT"})

    summary = service.run_hourly_import()

    assert summary.profile_fetch_attempts == 2
    assert summary.fetched_profiles == 1
    assert summary.profile_failures == 1


def test_force_profile_refresh_ignores_cache(monkeypatch) -> None:
    monkeypatch.setattr("src.services.import_service.normalize_insider_trade", lambda item, fetched_at: item)

    service, enrichment, _repo = _build_service(cached_company_keys={"AAPL", "MSFT"})

    summary = service.run_hourly_import(force_profile_refresh=True)

    assert summary.profile_cache_hits == 0
    assert summary.profile_fetch_attempts == 2
    assert summary.fetched_profiles == 2
    assert sorted(enrichment.calls) == ["AAPL", "MSFT"]


def test_default_behavior_keeps_respecting_cache(monkeypatch) -> None:
    monkeypatch.setattr("src.services.import_service.normalize_insider_trade", lambda item, fetched_at: item)

    service, enrichment, repo = _build_service(cached_company_keys={"AAPL", "MSFT"})

    summary = service.run_hourly_import()

    assert summary.profile_cache_hits == 2
    assert summary.profile_fetch_attempts == 0
    assert enrichment.calls == []
    assert len(repo.cache_checks) == 2
