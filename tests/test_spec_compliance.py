"""Spec-Compliance-Tests: Gate-Minimum 100k, API2 nur fuer PASS, 3-Tage-Akkumulation.

Diese Tests sichern die fachlichen Kernregeln ab, die laut Spezifikation
unveraendert gelten muessen.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from src.preprocessing.gate_evaluator import GateEvaluator, GateRules
from src.services.accumulation_service import AccumulationService
from src.services.import_service import ImportService
from src.services.app_settings_service import RuntimeSettings
from src.config.settings import DEFAULT_GATE_MIN_TRADE_VALUE
from src.services.transaction_code_classifier import (
    CORE_BUY,
    CORE_SELL,
    EXCLUDE_FROM_CORE,
    MANUAL_REVIEW,
    SECONDARY_SIGNAL,
    TransactionCodeClassifier,
)


# ---------------------------------------------------------------------------
# 1. Gate-Minimum muss 100.000 sein
# ---------------------------------------------------------------------------

def test_gate_min_trade_value_default_is_100k() -> None:
    """Spezifikation: Gate-Minimum Trade Value = $100.000."""
    assert DEFAULT_GATE_MIN_TRADE_VALUE == 100_000


def test_gate_rules_default_min_trade_value_is_100k() -> None:
    """GateRules-Default muss $100.000 sein."""
    rules = GateRules()
    assert rules.min_trade_value == 100_000


def test_gate_evaluator_rejects_below_100k() -> None:
    """Trades unter $100.000 muessen PRE_GATE_FAIL erhalten."""
    evaluator = GateEvaluator()
    trade = {
        "symbol": "AAPL",
        "filing_date": "2026-01-10",
        "transaction_date": "2026-01-08",
        "qty": 100,
        "price": 500.0,
        "trade_value": 50_000,  # unter 100k
        "form_type": "4",
        "acquisition_or_disposition": "A",
        "transaction_type": "P-Purchase",
        "filing_age_days": 2,
        "security_name": "Apple Inc Common Stock",  # -> STOCK
        "is_actively_trading": True,
    }
    result = evaluator.evaluate(trade)
    assert result.status == "PRE_GATE_FAIL"
    assert result.reason == "trade_value_below_threshold"


def test_gate_evaluator_passes_at_exactly_100k() -> None:
    """Trade exakt an der Schwelle $100.000 soll PASS erhalten (Gate ist strict <, nicht <=)."""
    evaluator = GateEvaluator()
    trade = {
        "symbol": "MSFT",
        "filing_date": "2026-01-10",
        "transaction_date": "2026-01-08",
        "qty": 200,
        "price": 500.0,
        "trade_value": 100_000,
        "form_type": "4",
        "acquisition_or_disposition": "A",
        "transaction_type": "P-Purchase",
        "filing_age_days": 2,
        "security_name": "Microsoft Common Stock",  # -> STOCK
        "is_actively_trading": True,
    }
    result = evaluator.evaluate(trade)
    # Gate: trade_value < min_trade_value => FAIL. 100k == 100k => nicht kleiner => PASS
    assert result.status == "PASS", f"Exakt 100k soll PASS ergeben aber war: {result.status} ({result.reason})"


# ---------------------------------------------------------------------------
# 2. API2 darf nicht fuer PRE_GATE_FAIL-Trades aufgerufen werden
# ---------------------------------------------------------------------------

def test_runtime_settings_api2_firing_mode_default_is_only_pass() -> None:
    """RuntimeSettings-Default muss ONLY PASS sein."""
    rs = RuntimeSettings(
        min_trade_value=100_000,
        require_purchase_event=True,
        require_common_stock=True,
        allowed_acquisition_or_disposition=("A",),
        allowed_transaction_types=(),
        profile_gate_filter_statuses=("PASS",),
        profile_ttl_days=7,
        lookup_mode="cik_primary_symbol_fallback",
    )
    assert rs.api2_firing_mode == "ONLY PASS"


def test_import_service_default_api2_mode_is_only_pass() -> None:
    """ImportService-Default api2_firing_mode muss ONLY PASS sein."""
    import inspect
    sig = inspect.signature(ImportService.__init__)
    default = sig.parameters["api2_firing_mode"].default
    assert default == "ONLY PASS", f"Erwartet 'ONLY PASS', bekommen: {default!r}"


def test_import_service_skips_api2_for_pre_gate_fail(monkeypatch) -> None:
    """API2 darf bei PRE_GATE_FAIL-Trades nicht aufgerufen werden."""
    from dataclasses import dataclass

    @dataclass
    class _Decision:
        status: str
        reason: str = "value_below_threshold"

    class _GateFail:
        def evaluate(self, _: dict) -> _Decision:
            return _Decision(status="PRE_GATE_FAIL")

    class _RawRepo:
        def upsert_raw_trades(self, trades: list[dict]) -> int:
            return len(trades)

    class _CompanyMongoRepo:
        def __init__(self):
            self.calls = []

        def get_recent_profile(self, key: str, ttl_days: int):
            return None

        def get_bulk_recent_profiles(self, keys, ttl_days: int):
            return {}

        def upsert_profile(self, profile: dict) -> None:
            self.calls.append(profile)

    api2_called = {"count": 0}

    class _FmpClient:
        def fetch_latest_insider_trades(self, page=0, limit=100):
            return [{
                "symbol": "LOW_VAL",
                "reportingName": "Test Insider",
                "transactionDate": "2026-01-08",
                "filingDate": "2026-01-10",
                "securitiesTransacted": 10,
                "price": 10.0,
                "transactionType": "P-Purchase",
                "acquisitionOrDisposition": "A",
                "formType": "4",
            }]

        def fetch_company_profile(self, symbol: str, **kwargs):
            api2_called["count"] += 1
            return {}

        def fetch_profile_by_cik(self, cik: str, **kwargs):
            api2_called["count"] += 1
            return {}

    mongo_repo = _CompanyMongoRepo()

    svc = ImportService(
        fmp_client=_FmpClient(),
        gate_evaluator=_GateFail(),
        raw_repo=_RawRepo(),
        company_mongo_repo=mongo_repo,
        trade_mysql_repo=None,
        company_mysql_repo=None,
        api2_firing_mode="ONLY PASS",
        allow_write=True,
    )

    monkeypatch.setattr("src.services.import_service.normalize_insider_trade", lambda item, fetched_at: {
        "symbol": item.get("symbol", ""),
        "gate_status": "PRE_GATE_FAIL",
        "company_key": "LOW_VAL::CIK_UNKNOWN",
    })

    try:
        svc.run_hourly_import()
    except Exception:
        pass  # DB-writes koennen fehlen – das ist hier nicht das Testziel

    assert api2_called["count"] == 0, "API2 darf nicht fuer PRE_GATE_FAIL aufgerufen werden."


# ---------------------------------------------------------------------------
# 3. 3-Tage-Akkumulation: kein A/D-Mix, korrekte Gruppierung
# ---------------------------------------------------------------------------

def _make_trade_df(rows: list[dict]) -> pd.DataFrame:
    base = {
        "symbol_at_trade": "AAPL",
        "reporting_name": "Jane Insider",
        "acquisition_or_disposition": "A",
        "normalized_instrument_type": "OPERATING_COMPANY_EQUITY",
    }
    records = []
    for r in rows:
        rec = dict(base)
        rec.update(r)
        records.append(rec)
    return pd.DataFrame(records)


def test_accumulation_window_is_3_days_default() -> None:
    """Das default window_days muss 3 sein."""
    import inspect
    sig = inspect.signature(AccumulationService.accumulate_trades)
    assert sig.parameters["window_days"].default == 3


def test_accumulation_does_not_mix_buy_and_sell() -> None:
    """Kaeufe (A) und Verkaeufe (D) duerfen nicht in dieselbe Gruppe akkumuliert werden."""
    today = date(2026, 4, 1)
    df = _make_trade_df([
        {"transaction_date": str(today), "acquisition_or_disposition": "A", "trade_value_estimated": 200_000},
        {"transaction_date": str(today + timedelta(days=1)), "acquisition_or_disposition": "D", "trade_value_estimated": 150_000},
    ])
    result = AccumulationService.tag_trades_with_groups(df, window_days=3)
    groups = result["accumulation_group_id"].unique()
    assert len(groups) == 2, "A und D duerfen nicht in dieselbe Gruppe fallen."


def test_accumulation_groups_trades_within_3_days() -> None:
    """Trades innerhalb von 3 Tagen (gleiche Person/Symbol/Richtung) sollen eine Gruppe bilden; ab 4 Tagen Abstand eine neue."""
    today = date(2026, 4, 1)
    df = _make_trade_df([
        {"transaction_date": str(today), "trade_value_estimated": 100_000},
        {"transaction_date": str(today + timedelta(days=2)), "trade_value_estimated": 100_000},
        # Tag 0 + 2 = 2 Tage Abstand: gleiche Gruppe
        # Tag 2 + 4 = 4 Tage Abstand zum vorherigen: neue Gruppe
        {"transaction_date": str(today + timedelta(days=6)), "trade_value_estimated": 100_000},
    ])
    result = AccumulationService.tag_trades_with_groups(df, window_days=3)
    groups = result["accumulation_group_id"].unique()
    assert len(groups) == 2, f"Tag 0+2 sollen eine Gruppe bilden, Tag 6 eine neue, aber bekommen: {sorted(groups)}"


def test_accumulation_splits_group_when_gap_exceeds_3_days() -> None:
    """Eine Zeitluecke > 3 Tage muss eine neue Gruppe erzeugen."""
    today = date(2026, 4, 1)
    df = _make_trade_df([
        {"transaction_date": str(today), "trade_value_estimated": 100_000},
        {"transaction_date": str(today + timedelta(days=5)), "trade_value_estimated": 100_000},
    ])
    result = AccumulationService.tag_trades_with_groups(df, window_days=3)
    groups = result["accumulation_group_id"].unique()
    assert len(groups) == 2


@pytest.mark.parametrize(
    ("tx", "expected"),
    [
        ("P-Purchase", CORE_BUY),
        ("S-Sale", CORE_SELL),
        ("I-Discretionary", SECONDARY_SIGNAL),
        ("L-Small", SECONDARY_SIGNAL),
        ("J-Other", MANUAL_REVIEW),
        ("V-Voluntary", MANUAL_REVIEW),
        ("A-Award", EXCLUDE_FROM_CORE),
        ("M-Exempt", EXCLUDE_FROM_CORE),
        ("F-Tax", EXCLUDE_FROM_CORE),
        ("G-Gift", EXCLUDE_FROM_CORE),
    ],
)
def test_transaction_code_classifier_matrix(tx: str, expected: str) -> None:
    info = TransactionCodeClassifier.classify(tx)
    assert info.classification == expected


@pytest.mark.parametrize("tx", ["A-Award", "M-Exempt", "F-Tax", "G-Gift"])
def test_gate_evaluator_rejects_excluded_transaction_code_class(tx: str) -> None:
    evaluator = GateEvaluator()
    trade = {
        "symbol": "AAPL",
        "filing_date": "2026-01-10",
        "transaction_date": "2026-01-08",
        "qty": 200,
        "price": 500.0,
        "trade_value": 100_000,
        "form_type": "4",
        "acquisition_or_disposition": "A",
        "transaction_type": tx,
        "filing_age_days": 2,
        "security_name": "Apple Common Stock",
        "is_actively_trading": True,
    }
    result = evaluator.evaluate(trade)
    assert result.status == "PRE_GATE_FAIL"
    assert result.reason in {"excluded_transaction_code_class", "excluded_transaction_type"}




