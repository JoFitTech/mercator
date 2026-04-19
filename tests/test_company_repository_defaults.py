from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from src.db.repositories.company_repository import CompanyRepository
from src.services.import_service import ImportService


class _DummyClient:
    def __init__(self) -> None:
        self.last_sql = None
        self.last_params = None

    def execute(self, sql, params):
        self.last_sql = sql
        self.last_params = params
        return 1


def test_company_repository_defaults_sector_resolution_status_when_missing() -> None:
    dummy_client = _DummyClient()
    repo = CompanyRepository(cast(Any, dummy_client))
    repo.upsert_company({"company_key": "SYM:AAPL", "current_symbol": "AAPL"})

    assert dummy_client.last_params is not None
    assert dummy_client.last_params["sector_resolution_status"] == "UNRESOLVED"


def test_company_repository_defaults_sector_resolution_status_when_none() -> None:
    dummy_client = _DummyClient()
    repo = CompanyRepository(cast(Any, dummy_client))
    repo.upsert_company(
        {
            "company_key": "SYM:AAPL",
            "current_symbol": "AAPL",
            "sector_resolution_status": None,
        }
    )

    assert dummy_client.last_params is not None
    assert dummy_client.last_params["sector_resolution_status"] == "UNRESOLVED"


def test_import_service_stub_sets_unresolved_sector_status() -> None:
    class _MongoRepo:
        def __init__(self) -> None:
            self.last_payload = None

        def upsert_profile(self, payload):
            self.last_payload = payload

    class _CompanyRepo:
        def __init__(self) -> None:
            self.last_payload = None

        def upsert_company(self, payload):
            self.last_payload = payload

    mongo_repo = _MongoRepo()
    company_repo = _CompanyRepo()

    service = ImportService(
        fmp_client=cast(Any, object()),
        gate_evaluator=cast(Any, object()),
        raw_repo=cast(Any, object()),
        company_mongo_repo=cast(Any, mongo_repo),
        trade_mysql_repo=None,
        company_mysql_repo=cast(Any, company_repo),
    )

    fetched_at = datetime.now(timezone.utc)
    service._upsert_company_stub(
        {
            "company_key": "SYM:MSFT",
            "company_cik": "0000789019",
            "symbol": "MSFT",
        },
        fetched_at,
    )

    assert mongo_repo.last_payload is not None
    assert company_repo.last_payload is not None
    assert mongo_repo.last_payload["sector_resolution_status"] == "UNRESOLVED"
    assert company_repo.last_payload["sector_resolution_status"] == "UNRESOLVED"


