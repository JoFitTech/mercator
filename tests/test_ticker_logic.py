import unittest
from unittest.mock import MagicMock
import pandas as pd
from src.services.analysis_service import AnalysisService
from src.preprocessing.gate_evaluator import GATE_PASS, GATE_PENDING, GATE_FAIL
from src.models.analysis_result import AnalysisResult

class TestTickerLogic(unittest.TestCase):
    def setUp(self):
        self.trade_repo = MagicMock()
        self.company_repo = MagicMock()
        self.fmp_client = MagicMock()
        self.service = AnalysisService(
            trade_repo=self.trade_repo,
            company_repo=self.company_repo,
            fmp_client=self.fmp_client
        )

    def test_list_ticker_options_filters_properly(self):
        # Mock liefert Symbole und CIKs
        self.trade_repo.fetch_all_symbols.return_value = ["AAPL", "TSLA", "CIK:12345", "123456", ""]
        
        # list_ticker_options sollte nur AAPL und TSLA liefern
        options = self.service.list_ticker_options()
        self.assertEqual(options, ["AAPL", "TSLA"])
        
        # Company repo sollte NICHT mehr abgefragt werden für die Ticker-Liste
        self.company_repo.fetch_all_symbols.assert_not_called()

    def test_get_ticker_detail_enrichment_logic(self):
        # Case 1: Symbol mit PASS Trade -> Enrichment erlaubt
        df_pass = pd.DataFrame([
            {"symbol": "AAPL", "gate_status": "PASS", "price": 150.0, "qty": 100}
        ])
        self.trade_repo.fetch_trades.return_value = df_pass
        self.company_repo.get_company_by_current_symbol.return_value = {"company_name": "Apple"}
        
        result = self.service.get_ticker_detail("AAPL")
        self.assertTrue(result.metrics["can_enrich"])
        self.assertEqual(result.metrics["overall_status"], "PASS")
        self.assertEqual(result.company_profile["company_name"], "Apple")

        # Case 2: Symbol mit nur FAIL Trades -> Enrichment verboten
        df_fail = pd.DataFrame([
            {"symbol": "FAIL_CO", "gate_status": "FAIL", "price": 10.0, "qty": 10}
        ])
        self.trade_repo.fetch_trades.return_value = df_fail
        
        result = self.service.get_ticker_detail("FAIL_CO")
        self.assertFalse(result.metrics["can_enrich"])
        self.assertEqual(result.metrics["overall_status"], "FAIL")
        self.assertEqual(result.company_profile, {})

        # Case 3: Symbol mit HOLD (PENDING) Trade -> Enrichment erlaubt
        df_hold = pd.DataFrame([
            {"symbol": "HOLD_CO", "gate_status": "PENDING", "price": 50.0, "qty": 50}
        ])
        self.trade_repo.fetch_trades.return_value = df_hold
        self.company_repo.get_company_by_current_symbol.return_value = {"company_name": "Holdings Inc"}
        
        result = self.service.get_ticker_detail("HOLD_CO")
        self.assertTrue(result.metrics["can_enrich"])
        self.assertEqual(result.metrics["overall_status"], "HOLD")
        self.assertEqual(result.company_profile["company_name"], "Holdings Inc")

    def test_invalid_symbol_handling(self):
        # CIK als Eingabe sollte gefiltert werden
        result = self.service.get_ticker_detail("CIK:000123")
        self.assertEqual(result.note, "Ungültiges Symbol.")
        self.assertEqual(result.company_profile, {})

if __name__ == "__main__":
    unittest.main()
