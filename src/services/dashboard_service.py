"""Dashboard-Service für KPIs und Diagrammdaten."""

from __future__ import annotations

import pandas as pd

from src.db.mongo_repository import CompanyMongoRepository, InsiderTradeMongoRepository
from src.db.mysql_repository import CompanyMySqlRepository, InsiderTradeMySqlRepository


class DashboardService:
    """Erzeugt Dashboard-Kennzahlen aus MongoDB und MySQL."""

    def __init__(
        self,
        raw_repo: InsiderTradeMongoRepository | None,
        company_mongo_repo: CompanyMongoRepository | None,
        trade_repo: InsiderTradeMySqlRepository,
        company_repo: CompanyMySqlRepository,
    ) -> None:
        self.raw_repo = raw_repo
        self.company_mongo_repo = company_mongo_repo
        self.trade_repo = trade_repo
        self.company_repo = company_repo

    def build_dashboard_payload(self) -> dict:
        """Liefert KPIs und vorbereitete DataFrames für Charts."""
        trades_df = self.trade_repo.fetch_trades(limit=5000)
        raw_records = 0
        gate_pass_records = 0
        
        if self.raw_repo is not None:
            try:
                raw_records = self.raw_repo.count_all()
            except Exception:
                raw_records = 0
        
        # Gate-PASS berechnen
        if not trades_df.empty and "gate_status" in trades_df.columns:
            gate_pass_records = trades_df[trades_df["gate_status"].astype(str).str.upper() == "PASS"].shape[0]

        payload = {
            "raw_records": raw_records,
            "clean_records": self.trade_repo.count_all(),
            "company_profiles": self.company_repo.count_all(),
            "gate_pass_records": gate_pass_records,
            "transaction_type_distribution": pd.DataFrame(),
            "sector_distribution": pd.DataFrame(),
            "timeline_distribution": pd.DataFrame(),
            "buy_sell_volume": pd.DataFrame(),
            "trades": trades_df,
        }

        if trades_df.empty:
            return payload

        # Vorbereitungen für Charts
        date_col = "transaction_date" if "transaction_date" in trades_df.columns else "filing_date"
        if date_col not in trades_df.columns:
            trades_df["event_date"] = pd.NaT
        else:
            trades_df["event_date"] = pd.to_datetime(trades_df[date_col], errors="coerce").dt.date

        if "acquisition_or_disposition" in trades_df.columns:
            trades_df["direction"] = (
                trades_df["acquisition_or_disposition"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                .map({"A": "BUY", "BUY": "BUY", "D": "SELL", "SELL": "SELL"})
                .fillna("UNKNOWN")
            )
        else:
            trades_df["direction"] = "UNKNOWN"

        if "trade_value_estimated" not in trades_df.columns:
            trades_df["trade_value_estimated"] = 0

        if "sector" not in trades_df.columns:
            trades_df["sector"] = "Unknown"
        trades_df["sector"] = trades_df["sector"].fillna("").astype(str)
        trades_df["sector"] = trades_df["sector"].str.strip().replace("", "Unknown")

        # 1. Transaktionstypen
        payload["transaction_type_distribution"] = (
            trades_df.groupby("transaction_type", dropna=False).size().reset_index(name="count")
        )
        # 2. Sektoren
        payload["sector_distribution"] = (
            trades_df.groupby("sector", dropna=False).size().reset_index(name="count")
        )
        # 3. Zeitverlauf nach Typ (Akkumuliertes Volumen pro Tag)
        payload["buy_sell_volume"] = (
            trades_df.groupby(["event_date", "direction"])["trade_value_estimated"]
            .sum()
            .reset_index()
            .pivot(index="event_date", columns="direction", values="trade_value_estimated")
            .fillna(0)
            .reset_index()
        )
        
        # 4. Zeitverlauf Anzahl (Filing Date oder Transaction Date)
        timeline_col = "filing_date" if "filing_date" in trades_df.columns else date_col
        payload["timeline_distribution"] = (
            trades_df.assign(e_date=pd.to_datetime(trades_df[timeline_col], errors="coerce").dt.date)
            .groupby("e_date", dropna=False)
            .size()
            .reset_index(name="count")
        )
        
        return payload
