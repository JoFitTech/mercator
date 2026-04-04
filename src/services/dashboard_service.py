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
        trades_df = self.trade_repo.fetch_trades(limit=2000)
        raw_records = 0
        gate_pass_records = 0
        
        if self.raw_repo is not None:
            try:
                raw_records = self.raw_repo.count_all()
            except Exception:
                # TODO: Logging ergänzen, sobald zentrales UI-Logging definiert ist.
                raw_records = 0
        
        # Gate-PASS berechnen (PASS, PROFILE_FETCHED, PROFILE_FETCH_FAILED)
        if not trades_df.empty:
            pass_statuses = {"PASS", "PROFILE_FETCHED", "PROFILE_FETCH_FAILED"}
            gate_pass_records = trades_df[trades_df["gate_status"].str.upper().isin(pass_statuses)].shape[0]

        payload = {
            "raw_records": raw_records,
            "clean_records": self.trade_repo.count_all(),
            "company_profiles": self.company_repo.count_all(),
            "gate_pass_records": gate_pass_records,
            "transaction_type_distribution": pd.DataFrame(),
            "sector_distribution": pd.DataFrame(),
            "timeline_distribution": pd.DataFrame(),
            "trades": trades_df,
        }

        if trades_df.empty:
            return payload

        payload["transaction_type_distribution"] = (
            trades_df.groupby("transaction_type", dropna=False).size().reset_index(name="count")
        )
        payload["sector_distribution"] = (
            trades_df.groupby("sector", dropna=False).size().reset_index(name="count")
        )
        timeline_col = "filing_date" if "filing_date" in trades_df.columns else "transaction_date"
        payload["timeline_distribution"] = (
            trades_df.assign(event_date=pd.to_datetime(trades_df[timeline_col], errors="coerce").dt.date)
            .groupby("event_date", dropna=False)
            .size()
            .reset_index(name="count")
        )
        return payload
