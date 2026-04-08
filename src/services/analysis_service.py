"""Analyse-Service für UI-taugliche Aggregationen."""

from __future__ import annotations

import pandas as pd

from src.db.mysql_repository import CompanyMySqlRepository, InsiderTradeMySqlRepository
from src.models.analysis_result import AnalysisResult
from src.services.accumulation_service import AccumulationService


class AnalysisService:
    """Bereitet Trade- und Unternehmensdaten für Explorer und Ticker-Details auf."""

    def __init__(
        self,
        trade_repo: InsiderTradeMySqlRepository,
        company_repo: CompanyMySqlRepository,
    ) -> None:
        self.trade_repo = trade_repo
        self.company_repo = company_repo

    def get_filtered_trades(
        self, 
        filters: dict | None = None, 
        limit: int = 500,
        accumulate: bool = True,
        min_value: float = 0
    ) -> pd.DataFrame:
        """Lädt bereinigte Trades mit optionalen Filtern und Akkumulation."""
        df = self.trade_repo.fetch_trades(filters=filters, limit=limit)
        
        if df.empty:
            return df

        # Datentypen sicherstellen
        df["trade_value_estimated"] = pd.to_numeric(df["trade_value_estimated"], errors="coerce")
        df["qty"] = pd.to_numeric(df["qty"], errors="coerce")
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

        # Richtung mappen (A -> BUY, D -> SELL)
        if "direction" not in df.columns and "acquisition_or_disposition" in df.columns:
            df["direction"] = df["acquisition_or_disposition"].apply(
                lambda x: "BUY" if x == "A" else ("SELL" if x == "D" else "UNKNOWN")
            )

        # Invariante A & F sicherstellen: Filter auf Rohdaten vor Aggregation
        if min_value > 0:
            df = df[df["trade_value_estimated"] >= min_value]

        if accumulate and not df.empty:
            return AccumulationService.accumulate_trades(df)
            
        return df

    def get_ticker_detail(self, company_key: str, accumulate: bool = True) -> AnalysisResult:
        """Liefert Profil, letzte Trades und Basiskennzahlen für einen Company-Key."""
        trades = self.trade_repo.fetch_trades(filters={"company_key": company_key}, limit=500)
        profile_df = self.company_repo.fetch_company(company_key)

        if not trades.empty:
            # Richtung mappen
            if "direction" not in trades.columns and "acquisition_or_disposition" in trades.columns:
                trades["direction"] = trades["acquisition_or_disposition"].apply(
                    lambda x: "BUY" if x == "A" else ("SELL" if x == "D" else "UNKNOWN")
                )
            
            # Tagging der Rohdaten für Detail-Matching ( Progressive Disclosure)
            trades = AccumulationService.tag_trades_with_groups(trades)

        if accumulate and not trades.empty:
            display_trades = AccumulationService.accumulate_trades(trades)
        else:
            display_trades = trades

        metrics = {
            "trade_count": int(len(trades)),
            "avg_price": float(trades["price"].dropna().mean()) if not trades.empty and not trades["price"].dropna().empty else None,
            "total_qty": float(trades["qty"].dropna().sum()) if not trades.empty and not trades["qty"].dropna().empty else None,
        }
        rows = display_trades.to_dict(orient="records")
        # Rohdaten mit Group-ID mitschicken
        raw_rows = trades.to_dict(orient="records")
        
        profile = profile_df.iloc[0].to_dict() if not profile_df.empty else {}
        note = "Keine Profildaten gefunden." if profile_df.empty else "Profildaten verfügbar."
        
        return AnalysisResult(
            title=f"Ticker-Detail {company_key}",
            metrics=metrics,
            rows=rows,
            raw_rows=raw_rows,
            company_profile=profile,
            note=note,
        )
