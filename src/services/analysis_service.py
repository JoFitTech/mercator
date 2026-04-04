"""Analyse-Service für UI-taugliche Aggregationen."""

from __future__ import annotations

import pandas as pd

from src.db.mysql_repository import CompanyMySqlRepository, InsiderTradeMySqlRepository
from src.models.analysis_result import AnalysisResult


class AnalysisService:
    """Bereitet Trade- und Unternehmensdaten für Explorer und Ticker-Details auf."""

    def __init__(
        self,
        trade_repo: InsiderTradeMySqlRepository,
        company_repo: CompanyMySqlRepository,
    ) -> None:
        self.trade_repo = trade_repo
        self.company_repo = company_repo

    def get_filtered_trades(self, filters: dict | None = None, limit: int = 500) -> pd.DataFrame:
        """Lädt bereinigte Trades mit optionalen Filtern."""
        return self.trade_repo.fetch_trades(filters=filters, limit=limit)

    def get_ticker_detail(self, symbol: str) -> AnalysisResult:
        """Liefert Profil, letzte Trades und Basiskennzahlen für ein Symbol."""
        trades = self.trade_repo.fetch_trades(filters={"symbol": symbol}, limit=50)
        profile_df = self.company_repo.fetch_company(symbol)

        metrics = {
            "trade_count": int(len(trades)),
            "avg_price": float(trades["price"].dropna().mean()) if not trades.empty and not trades["price"].dropna().empty else None,
            "total_qty": float(trades["qty"].dropna().sum()) if not trades.empty and not trades["qty"].dropna().empty else None,
        }
        rows = trades.to_dict(orient="records")
        profile = profile_df.iloc[0].to_dict() if not profile_df.empty else {}
        note = "Keine Profildaten gefunden." if profile_df.empty else "Profildaten verfügbar."
        return AnalysisResult(
            title=f"Ticker-Detail {symbol}",
            metrics=metrics,
            rows=rows,
            company_profile=profile,
            note=note,
        )
