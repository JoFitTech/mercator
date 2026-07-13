from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.services.stock_import_service import StockImportService


class _FmpStub:
    def __init__(self, *, profile=None, prices=None, income=None, key_metrics=None, ratios=None, fail: bool = False):
        self.profile = profile
        self.prices = prices or []
        self.income = income or []
        self.key_metrics = key_metrics or []
        self.ratios = ratios or []
        self.fail = fail

    def fetch_company_profile(self, symbol: str):
        if self.fail:
            raise RuntimeError("provider down")
        return self.profile

    def fetch_historical_price_eod_full(self, symbol: str, date_from: str, date_to: str):  # noqa: ARG002
        return self.prices

    def fetch_income_statement(self, symbol: str):  # noqa: ARG002
        return self.income

    def fetch_key_metrics(self, symbol: str):  # noqa: ARG002
        return self.key_metrics

    def fetch_ratios(self, symbol: str):  # noqa: ARG002
        return self.ratios


class _RawRepo:
    def __init__(self):
        self.responses = []

    def upsert_response(self, response):
        self.responses.append(response)
        return response.request_hash


class _CompanyRepo:
    def __init__(self):
        self.rows = []

    def upsert_company(self, row):
        self.rows.append(row)


class _PriceRepo:
    def __init__(self):
        self.rows = []

    def upsert_prices(self, rows):
        self.rows.extend(rows)
        return len(rows)


class _MetricsRepo:
    def __init__(self):
        self.rows = []

    def upsert_metrics(self, rows):
        self.rows.extend(rows)
        return len(rows)


class _ImportRunRepo:
    def __init__(self):
        self.runs = []

    def upsert_run(self, run):
        self.runs.append(replace(run))
        return run.import_run_id


class _DataQualityRepo:
    def __init__(self):
        self.issues = []

    def create_issue(self, issue):
        self.issues.append(issue)
        return len(self.issues)


def _build_service(fmp):
    raw = _RawRepo()
    company = _CompanyRepo()
    prices = _PriceRepo()
    metrics = _MetricsRepo()
    runs = _ImportRunRepo()
    issues = _DataQualityRepo()
    service = StockImportService(
        fmp_client=fmp,
        raw_repository=raw,
        company_repository=company,
        price_repository=prices,
        metrics_repository=metrics,
        import_run_repository=runs,
        data_quality_repository=issues,
    )
    return service, raw, company, prices, metrics, runs, issues


def test_stock_import_service_writes_raw_before_clean_records() -> None:
    service, raw, company, prices, metrics, runs, issues = _build_service(
        _FmpStub(
            profile={"symbol": "AAPL", "companyName": "Apple Inc.", "marketCap": 1000},
            prices=[{"date": "2026-07-08", "close": 204}],
            income=[{"date": "2025-12-31", "revenue": 100}],
            key_metrics=[{"date": "2025-12-31", "marketCap": 1000}],
            ratios=[{"date": "2025-12-31", "grossProfitMargin": 0.45}],
        )
    )

    summary = service.import_symbol("aapl", date_from="2026-07-01", date_to="2026-07-09")

    assert summary.status == "SUCCESS"
    assert summary.symbols_succeeded == 1
    assert summary.raw_responses_written == 5
    assert summary.clean_records_written == 5
    assert [response.category for response in raw.responses] == [
        "company_profile",
        "historical_price",
        "income_statement",
        "key_metrics",
        "ratios",
    ]
    assert company.rows[0]["current_symbol"] == "AAPL"
    assert prices.rows[0]["price_date"] == date(2026, 7, 8)
    assert {row["metric_name"] for row in metrics.rows} == {"revenue", "market_cap", "gross_margin"}
    assert [run.status for run in runs.runs] == ["PENDING", "SUCCESS"]
    assert issues.issues == []


def test_stock_import_service_records_partial_provider_data_as_quality_issues() -> None:
    service, raw, company, prices, metrics, runs, issues = _build_service(
        _FmpStub(profile=None, prices=[], income=[], key_metrics=[], ratios=[])
    )

    summary = service.import_symbol("msft", date_from="2026-07-01", date_to="2026-07-09")

    assert summary.status == "SUCCESS"
    assert summary.clean_records_written == 0
    assert len(raw.responses) == 5
    assert company.rows == []
    assert prices.rows == []
    assert metrics.rows == []
    assert {issue.data_category for issue in issues.issues} == {
        "company_profile",
        "historical_price",
        "financial_metrics",
    }
    assert [run.status for run in runs.runs] == ["PENDING", "SUCCESS"]


def test_stock_import_service_marks_failed_import_run_and_issue() -> None:
    service, raw, _company, _prices, _metrics, runs, issues = _build_service(_FmpStub(fail=True))

    summary = service.import_symbol("msft", date_from="2026-07-01", date_to="2026-07-09")

    assert summary.status == "FAILED"
    assert summary.symbols_failed == 1
    assert len(raw.responses) == 0
    assert [run.status for run in runs.runs] == ["PENDING", "FAILED"]
    assert issues.issues[0].data_category == "stock_import"
