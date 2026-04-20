import pytest
import pandas as pd
from datetime import datetime
from src.services.accumulation_service import AccumulationService


def test_accumulation_basic():
    data = [
        # Gruppe 1: Gleiche fachliche Keys, innerhalb 3 Tage
        {"symbol_at_trade": "AAPL", "reporting_name": "Person A", "transaction_date": "2026-04-01", "acquisition_or_disposition": "A", "transaction_type": "P-Purchase", "qty": 100, "price": 150, "trade_value_estimated": 15000, "security_name": "Common Stock", "validation_status": "VALID"},
        {"symbol_at_trade": "AAPL", "reporting_name": "Person A", "transaction_date": "2026-04-02", "acquisition_or_disposition": "A", "transaction_type": "P-Purchase", "qty": 200, "price": 155, "trade_value_estimated": 31000, "security_name": "Common Stock", "validation_status": "VALID"},
        {"symbol_at_trade": "AAPL", "reporting_name": "Person A", "transaction_date": "2026-04-05", "acquisition_or_disposition": "A", "transaction_type": "P-Purchase", "qty": 50, "price": 160, "trade_value_estimated": 8000, "security_name": "Common Stock", "validation_status": "VALID"},
        # Andere Richtung => eigene Gruppe
        {"symbol_at_trade": "AAPL", "reporting_name": "Person A", "transaction_date": "2026-04-01", "acquisition_or_disposition": "D", "transaction_type": "S-Sale", "qty": 10, "price": 150, "trade_value_estimated": 1500, "security_name": "Common Stock", "validation_status": "VALID"},
    ]
    df = pd.DataFrame(data)

    acc_df = AccumulationService.accumulate_trades(df)

    assert len(acc_df) == 2
    g_buy = acc_df[acc_df["acquisition_or_disposition"] == "A"].iloc[0]
    assert g_buy["accumulated_trade_count"] == 3
    assert g_buy["accumulated_qty"] == 350
    assert g_buy["accumulation_start_date"].date() == datetime(2026, 4, 1).date()
    assert g_buy["accumulation_end_date"].date() == datetime(2026, 4, 5).date()


def test_accumulation_weighted_average():
    data = [
        {"symbol_at_trade": "X", "reporting_name": "A", "transaction_date": "2026-01-01", "acquisition_or_disposition": "A", "transaction_type": "P-Purchase", "qty": 10, "price": 100, "trade_value_estimated": 1000, "security_name": "S", "validation_status": "VALID"},
        {"symbol_at_trade": "X", "reporting_name": "A", "transaction_date": "2026-01-02", "acquisition_or_disposition": "A", "transaction_type": "P-Purchase", "qty": 20, "price": 200, "trade_value_estimated": 4000, "security_name": "S", "validation_status": "VALID"},
    ]
    df = pd.DataFrame(data)
    acc_df = AccumulationService.accumulate_trades(df)

    assert acc_df.iloc[0]["accumulated_avg_price_weighted"] == pytest.approx(166.666666666)


def test_accumulation_excludes_price_invalid():
    data = [
        {"symbol_at_trade": "X", "reporting_name": "A", "transaction_date": "2026-01-01", "acquisition_or_disposition": "A", "transaction_type": "P-Purchase", "qty": 10, "price": 100, "trade_value_estimated": 1000, "security_name": "Common Stock", "validation_status": "PRICE_INVALID"},
        {"symbol_at_trade": "X", "reporting_name": "A", "transaction_date": "2026-01-02", "acquisition_or_disposition": "A", "transaction_type": "P-Purchase", "qty": 10, "price": 100, "trade_value_estimated": 1000, "security_name": "Common Stock", "validation_status": "VALID"},
    ]
    df = pd.DataFrame(data)
    acc_df = AccumulationService.accumulate_trades(df)

    assert len(acc_df) == 1
    assert acc_df.iloc[0]["accumulated_qty"] == 10


def test_accumulation_preserves_score_columns_for_ui() -> None:
    data = [
        {
            "symbol_at_trade": "AAPL",
            "reporting_name": "Person A",
            "transaction_date": "2026-04-01",
            "acquisition_or_disposition": "A",
            "transaction_type": "P-Purchase",
            "qty": "100",
            "price": "150",
            "trade_value_estimated": "15000",
            "score": 70,
            "security_name": "Common Stock",
            "validation_status": "VALID",
        },
        {
            "symbol_at_trade": "AAPL",
            "reporting_name": "Person A",
            "transaction_date": "2026-04-02",
            "acquisition_or_disposition": "A",
            "transaction_type": "P-Purchase",
            "qty": 50,
            "price": 160,
            "trade_value_estimated": 8000,
            "score": 90,
            "security_name": "Common Stock",
            "validation_status": "VALID",
        },
    ]
    df = pd.DataFrame(data)

    acc_df = AccumulationService.accumulate_trades(df)

    assert "score" in acc_df.columns
    assert "score_class" in acc_df.columns
    assert "score_mean" not in acc_df.columns
    assert "accumulation_start_date" in acc_df.columns
    assert "accumulation_end_date" in acc_df.columns


def test_accumulation_never_merges_mixed_a_d() -> None:
    df = pd.DataFrame(
        [
            {"symbol_at_trade": "AAPL", "reporting_name": "A", "acquisition_or_disposition": "A", "transaction_date": "2026-04-01", "qty": 10, "price": 100, "trade_value_estimated": 1000},
            {"symbol_at_trade": "AAPL", "reporting_name": "A", "acquisition_or_disposition": "D", "transaction_date": "2026-04-02", "qty": 10, "price": 100, "trade_value_estimated": 1000},
        ]
    )
    tagged = AccumulationService.tag_trades_with_groups(df, window_days=3)
    assert tagged["accumulation_group_id"].nunique() == 2


def test_accumulation_adds_multi_insider_cluster_metrics() -> None:
    df = pd.DataFrame(
        [
            {"symbol_at_trade": "AAPL", "reporting_name": "A", "acquisition_or_disposition": "A", "transaction_date": "2026-04-01", "qty": 10, "price": 100, "trade_value_estimated": 1000},
            {"symbol_at_trade": "AAPL", "reporting_name": "B", "acquisition_or_disposition": "A", "transaction_date": "2026-04-02", "qty": 10, "price": 100, "trade_value_estimated": 1000},
        ]
    )
    result = AccumulationService.accumulate_trades(df, window_days=3)
    assert "distinct_reporting_names_same_symbol_same_direction_3d" in result.columns
    assert result["distinct_reporting_names_same_symbol_same_direction_3d"].max() >= 2
    assert "accumulated_trade_count" in result.columns
    assert "accumulated_qty" in result.columns
    assert "accumulated_trade_value_estimated" in result.columns
    assert "accumulated_avg_price_weighted" in result.columns
