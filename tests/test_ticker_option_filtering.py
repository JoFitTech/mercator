from src.services.analysis_service import AnalysisService


class _TradeRepo:
    def fetch_all_symbols(self):
        return ["AAPL", "CIK:123", "000999", None, "msft"]

    def fetch_trades(self, filters=None, limit=500):
        raise AssertionError("not used")


class _CompanyRepo:
    def fetch_all_symbols(self):
        return ["AAPL", "TSLA", "US1234567890"]


def test_ticker_options_only_include_symbols() -> None:
    service = AnalysisService(_TradeRepo(), _CompanyRepo())
    assert service.list_ticker_options() == ["AAPL", "MSFT", "TSLA"]
