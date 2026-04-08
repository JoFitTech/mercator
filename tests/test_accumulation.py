import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.services.accumulation_service import AccumulationService

def test_accumulation_basic():
    # Setup data
    data = [
        # Gruppe 1: Gleiche Person, Gleiche Firma, konsekutive Tage
        {"reporting_name": "Person A", "symbol_at_trade": "AAPL", "transaction_date": "2026-04-01", "acquisition_or_disposition": "A", "qty": 100, "price": 150, "trade_value_estimated": 15000, "security_name": "Common Stock"},
        {"reporting_name": "Person A", "symbol_at_trade": "AAPL", "transaction_date": "2026-04-02", "acquisition_or_disposition": "A", "qty": 200, "price": 155, "trade_value_estimated": 31000, "security_name": "Common Stock"},
        
        # Gruppe 2: Gleiche Person, Gleiche Firma, aber Lücke > 1 Tag
        {"reporting_name": "Person A", "symbol_at_trade": "AAPL", "transaction_date": "2026-04-05", "acquisition_or_disposition": "A", "qty": 50, "price": 160, "trade_value_estimated": 8000, "security_name": "Common Stock"},
        
        # Gruppe 3: Andere Person
        {"reporting_name": "Person B", "symbol_at_trade": "AAPL", "transaction_date": "2026-04-01", "acquisition_or_disposition": "A", "qty": 1000, "price": 150, "trade_value_estimated": 150000, "security_name": "Common Stock"},
        
        # Gruppe 4: Andere Richtung
        {"reporting_name": "Person A", "symbol_at_trade": "AAPL", "transaction_date": "2026-04-01", "acquisition_or_disposition": "D", "qty": 10, "price": 150, "trade_value_estimated": 1500, "security_name": "Common Stock"},
    ]
    df = pd.DataFrame(data)
    
    # Run accumulation
    acc_df = AccumulationService.accumulate_trades(df)
    
    # Assertions
    assert len(acc_df) == 4
    
    # Check Gruppe 1 (aggregiert)
    g1 = acc_df[acc_df["accumulated_trade_count"] == 2].iloc[0]
    assert g1["accumulated_qty"] == 300
    assert g1["accumulated_trade_value_estimated"] == 46000
    assert g1["is_accumulated"] == True
    assert g1["accumulation_start_date"].date() == datetime(2026, 4, 1).date()
    assert g1["accumulation_end_date"].date() == datetime(2026, 4, 2).date()

def test_accumulation_weighted_average():
    data = [
        {"reporting_name": "A", "symbol_at_trade": "X", "transaction_date": "2026-01-01", "acquisition_or_disposition": "A", "qty": 10, "price": 100, "trade_value_estimated": 1000, "security_name": "S"},
        {"reporting_name": "A", "symbol_at_trade": "X", "transaction_date": "2026-01-02", "acquisition_or_disposition": "A", "qty": 20, "price": 200, "trade_value_estimated": 4000, "security_name": "S"},
    ]
    df = pd.DataFrame(data)
    acc_df = AccumulationService.accumulate_trades(df)
    
    # (10*100 + 20*200) / (10+20) = (1000 + 4000) / 30 = 5000 / 30 = 166.666...
    assert acc_df.iloc[0]["accumulated_avg_price_weighted"] == pytest.approx(166.666666666)

def test_accumulation_different_securities():
    data = [
        {"reporting_name": "A", "symbol_at_trade": "X", "transaction_date": "2026-01-01", "acquisition_or_disposition": "A", "qty": 10, "price": 100, "trade_value_estimated": 1000, "security_name": "Common Stock"},
        {"reporting_name": "A", "symbol_at_trade": "X", "transaction_date": "2026-01-01", "acquisition_or_disposition": "A", "qty": 10, "price": 100, "trade_value_estimated": 1000, "security_name": "Option"},
    ]
    df = pd.DataFrame(data)
    acc_df = AccumulationService.accumulate_trades(df)
    
    # Sollte 2 Gruppen ergeben
    assert len(acc_df) == 2
