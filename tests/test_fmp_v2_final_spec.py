from __future__ import annotations

from datetime import UTC, datetime

from src.preprocessing.gate_evaluator import GATE_FAIL, GATE_PASS, GATE_PENDING, GateEvaluator
from src.services.accumulation_service import AccumulationService
from src.services.company_profile_enrichment_service import CompanyProfileEnrichmentService
from src.services.historical_market_data_service import HistoricalMarketDataService
from src.services.security_normalization_service import SecurityNormalizationService
from src.services.transaction_code_classifier import (
    CORE_BUY,
    CORE_SELL,
    EXCLUDE_FROM_CORE,
    TransactionCodeClassifier,
)
from src.services.buy_engine import score_trade, STATUS_SELL_WARNING


def _trade(**overrides):
    base = {
        "symbol": "AAPL",
        "filing_date": datetime(2026, 4, 1, tzinfo=UTC),
        "transaction_date": datetime(2026, 4, 1, tzinfo=UTC),
        "qty": 1000,
        "price": 120.0,
        "trade_value": 120000.0,
        "trade_value_estimated": 120000.0,
        "form_type": "4",
        "security_name": "Common Stock",
        "normalized_instrument_type": "STOCK",
        "acquisition_or_disposition": "A",
    }
    base.update(overrides)
    return base


def test_validation_price_qty_symbol_rules() -> None:
    evaluator = GateEvaluator()
    assert evaluator.evaluate(_trade(price=0)).status == GATE_FAIL
    assert evaluator.evaluate(_trade(qty=0)).status == GATE_FAIL
    assert evaluator.evaluate(_trade(symbol="")).status == GATE_FAIL


def test_form_type_and_minimum_signal_rules() -> None:
    evaluator = GateEvaluator()
    assert evaluator.evaluate(_trade(form_type="3")).status == GATE_FAIL
    assert evaluator.evaluate(_trade(trade_value=99999, trade_value_estimated=99999)).status == GATE_FAIL


def test_filing_freshness_rules() -> None:
    evaluator = GateEvaluator()
    assert evaluator.evaluate(_trade(filing_age_days=46)).status == GATE_FAIL
    assert evaluator.evaluate(_trade(filing_age_days=22)).status == GATE_PENDING


def test_instrument_normalization_etf_allowed_adr_rejected() -> None:
    assert SecurityNormalizationService.normalize("ETF Shares") == "ETF"
    assert SecurityNormalizationService.is_allowed("ETF")
    assert SecurityNormalizationService.normalize("American Depositary Receipt") == "ADR"
    assert not SecurityNormalizationService.is_allowed("ADR")


def test_transaction_code_classification_matrix() -> None:
    assert TransactionCodeClassifier.classify("P-Purchase").classification == CORE_BUY
    assert TransactionCodeClassifier.classify("S-Sale").classification == CORE_SELL
    assert TransactionCodeClassifier.classify("A-Award").classification == EXCLUDE_FROM_CORE


def test_accumulation_never_mixes_a_and_d() -> None:
    import pandas as pd

    df = pd.DataFrame([
        {"symbol_at_trade": "AAPL", "reporting_name": "R", "acquisition_or_disposition": "A", "transaction_date": "2026-01-01", "qty": 10, "trade_value_estimated": 1000, "price": 100, "score": 50},
        {"symbol_at_trade": "AAPL", "reporting_name": "R", "acquisition_or_disposition": "D", "transaction_date": "2026-01-02", "qty": 10, "trade_value_estimated": 1000, "price": 100, "score": 50},
    ])
    tagged = AccumulationService.tag_trades_with_groups(df)
    assert tagged["accumulation_group_id"].nunique() == 2


def test_api2_fallback_uses_search_cik_then_profile_cik() -> None:
    class Stub:
        def fetch_company_profile(self, symbol):
            return {}

        def fetch_search_cik(self, symbol):
            return [{"cik": "0000320193"}]

        def fetch_company_profile_by_cik(self, cik):
            return {"companyName": "Apple Inc.", "cik": cik}

    service = CompanyProfileEnrichmentService(Stub())
    profile = service.fetch_profile("AAPL")
    assert profile and profile["companyName"] == "Apple Inc."


def test_api3_mapping_and_sorting() -> None:
    class Stub:
        def fetch_historical_price_eod_full(self, symbol, date_from, date_to):
            return [
                {"date": "2026-01-03", "close": 12, "volume": 150},
                {"date": "2026-01-01", "close": 10, "volume": 100},
                {"date": "2026-01-02", "close": 11, "volume": 120},
            ]

    signal = HistoricalMarketDataService(Stub()).load_signal("AAPL")
    assert signal.avg_20d_volume is not None


def test_scoring_sell_warning_for_s_code() -> None:
    result = score_trade(_trade(transaction_type="S-Sale", transaction_code_class="CORE_SELL", trade_value=2_000_000, trade_value_estimated=2_000_000))
    assert result.decision_status == STATUS_SELL_WARNING
