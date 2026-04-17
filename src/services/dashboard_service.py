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

    def build_dashboard_payload(self, filters: dict | None = None) -> dict:
        """Liefert KPIs und vorbereitete DataFrames für Charts basierend auf Filtern."""
        filters = filters or {}
        try:
            # Wir rufen fetch_trades mit Filtern auf
            trades_df = self.trade_repo.fetch_trades(limit=10000, filters=filters)
        except Exception:
            trades_df = pd.DataFrame()
            
        # Grundlegende Bereinigung/Transformation des DataFrames für das Dashboard
        trades_df = self._prepare_dataframe(trades_df)

        # KPIs berechnen (basierend auf dem gefilterten Scope)
        kpis = self._compute_kpis(trades_df)

        # Diagrammdaten vorbereiten (basierend auf dem gefilterten Scope)
        charts = self._prepare_charts(trades_df)

        payload = {
            **kpis,
            **charts,
            "trades": trades_df[trades_df["dashboard_valid"] == True] if "dashboard_valid" in trades_df.columns else trades_df,
            "last_update": self._get_last_update_str(trades_df),
        }
        
        return payload

    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Bereitet den DataFrame für die Dashboard-Logik vor."""
        if df.empty:
            return df

        # event_date erzeugen (transaction_date bevorzugt, sonst filing_date)
        if "transaction_date" in df.columns:
            df["event_date"] = pd.to_datetime(df["transaction_date"], errors="coerce").dt.date
        elif "filing_date" in df.columns:
            df["event_date"] = pd.to_datetime(df["filing_date"], errors="coerce").dt.date
        else:
            df["event_date"] = pd.NaT

        # direction normalisieren
        if "acquisition_or_disposition" in df.columns:
            df["direction"] = (
                df["acquisition_or_disposition"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                .map({"A": "BUY", "BUY": "BUY", "D": "SELL", "SELL": "SELL"})
                .fillna("UNKNOWN")
            )
        else:
            df["direction"] = "UNKNOWN"

        # trade_value_estimated sicherstellen
        if "trade_value_estimated" not in df.columns:
            df["trade_value_estimated"] = 0
        df["trade_value_estimated"] = pd.to_numeric(df["trade_value_estimated"], errors="coerce").fillna(0)

        # sector sicherstellen (für Charts und KPIs)
        if "sector" not in df.columns:
            df["sector"] = None
        
        # Dashboard Validity (falls nicht schon in der DB berechnet oder als Fallback)
        if "dashboard_valid" not in df.columns:
            # Fallback-Logik falls Spalte fehlt
            df["dashboard_valid"] = df.apply(
                lambda x: pd.notna(x.get("symbol")) and 
                          pd.notna(x.get("price")) and x.get("price", 0) > 0 and
                          pd.notna(x.get("qty")) and x.get("qty", 0) > 0 and
                          x.get("direction") != "UNKNOWN" and
                          pd.notna(x.get("sector")) and str(x.get("sector")).lower() not in ("unknown", "n/a", ""),
                axis=1
            )
        else:
            # Sicherstellen dass es boolean ist
            df["dashboard_valid"] = df["dashboard_valid"].astype(bool)

        return df

    def _compute_kpis(self, df: pd.DataFrame) -> dict:
        """Berechnet die Dashboard-KPIs."""
        if df.empty:
            return {
                "valid_trades_count": 0,
                "gate_passed_count": 0,
                "profile_count": 0,
                "buy_quote": 0.0,
                "avg_score": 0.0,
            }

        # Nur valide Trades für Dashboard-Metriken und Tabellenanzeige im Dashboard
        if "dashboard_valid" in df.columns:
            valid_df = df[df["dashboard_valid"] == True]
        else:
            valid_df = df # Fallback falls Spalte fehlt (sollte nicht passieren)
        
        gate_passed = valid_df[valid_df["gate_status"].astype(str).str.upper() == "PASS"].shape[0]
        
        # Profile: Anzahl der erfolgreich aufgelösten Profile im aktuellen Scope
        # (Hier: Eindeutige Symbole mit FETCHED Status oder vorhandenem Sektor)
        profiles = df[df["profile_status"].astype(str).str.upper() == "FETCHED"]["company_key"].nunique()
        
        buy_trades = valid_df[valid_df["direction"] == "BUY"].shape[0]
        buy_quote = (buy_trades / valid_df.shape[0]) if not valid_df.empty else 0.0
        
        avg_score = valid_df["score_value"].mean() if not valid_df.empty else 0.0

        return {
            "valid_trades_count": valid_df.shape[0],
            "gate_passed_count": gate_passed,
            "profile_count": profiles,
            "buy_quote": buy_quote,
            "avg_score": avg_score,
        }

    def _prepare_charts(self, df: pd.DataFrame) -> dict:
        """Bereitet Daten für die Diagramme vor."""
        charts = {
            "sector_distribution_buy": pd.DataFrame(),
            "sector_distribution_sell": pd.DataFrame(),
            "timeline_distribution": pd.DataFrame(),
        }
        
        if df.empty:
            return charts

        # Nur valide Trades für Charts
        valid_df = df[df["dashboard_valid"] == True].copy()
        
        if valid_df.empty:
            return charts

        # 1. Sektor-Verteilung BUY
        buy_df = valid_df[valid_df["direction"] == "BUY"]
        if not buy_df.empty:
            charts["sector_distribution_buy"] = (
                buy_df.groupby("sector").size().reset_index(name="count")
            )
            
        # 2. Sektor-Verteilung SELL
        sell_df = valid_df[valid_df["direction"] == "SELL"]
        if not sell_df.empty:
            charts["sector_distribution_sell"] = (
                sell_df.groupby("sector").size().reset_index(name="count")
            )

        # 3. Zeitverlauf Activity (BUY/SELL getrennt)
        if "event_date" in valid_df.columns:
            charts["timeline_distribution"] = (
                valid_df.groupby(["event_date", "direction"]).size().reset_index(name="count")
            )
            
        return charts

    def _get_last_update_str(self, df: pd.DataFrame) -> str | None:
        """Ermittelt den letzten Update-Zeitpunkt."""
        if df.empty or "event_date" not in df.columns:
            return None
        
        last_date = df["event_date"].max()
        if pd.notna(last_date):
            return last_date.strftime("%d.%m.%Y") if hasattr(last_date, "strftime") else str(last_date)
        return None
