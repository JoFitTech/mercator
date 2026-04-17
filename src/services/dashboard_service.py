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
        
        # WICHTIG: Wir erzwingen dashboard_valid = True NICHT mehr auf Query-Ebene,
        # damit wir auch invalide Trades für die Diagnose im Scope haben.
        if "dashboard_valid" in filters:
            del filters["dashboard_valid"]
            
        try:
            # Wir rufen fetch_trades mit Filtern auf (ohne dashboard_valid Filter)
            trades_df = self.trade_repo.fetch_trades(limit=10000, filters=filters)
        except Exception:
            trades_df = pd.DataFrame()
            
        # Grundlegende Bereinigung/Transformation des DataFrames
        trades_df = self._prepare_dataframe(trades_df)

        # Subsets bilden
        valid_df = pd.DataFrame()
        invalid_df = pd.DataFrame()
        
        if not trades_df.empty:
            valid_df = trades_df[trades_df["dashboard_valid"] == True].copy()
            invalid_df = trades_df[trades_df["dashboard_valid"] == False].copy()

        # KPIs berechnen (basierend auf valid_df)
        kpis = self._compute_kpis(valid_df, trades_df)

        # Diagrammdaten vorbereiten (basierend auf valid_df)
        charts = self._prepare_charts(valid_df)
        
        # Diagnose-Infos
        diagnostics = self._compute_diagnostics(trades_df, valid_df, invalid_df, filters)

        payload = {
            **kpis,
            **charts,
            **diagnostics,
            "trades_all_scoped": trades_df,
            "trades_valid": valid_df,
            "trades_invalid": invalid_df,
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

        # sector sicherstellen
        if "sector" not in df.columns:
            df["sector"] = None
        
        # Dashboard Validity
        if "dashboard_valid" not in df.columns:
            # Fallback-Logik
            df["dashboard_valid"] = df.apply(
                lambda x: pd.notna(x.get("symbol")) and 
                          pd.notna(x.get("price")) and x.get("price", 0) > 0 and
                          pd.notna(x.get("qty")) and x.get("qty", 0) > 0 and
                          x.get("direction") != "UNKNOWN" and
                          pd.notna(x.get("sector")) and str(x.get("sector")).lower() not in ("unknown", "n/a", "", "none"),
                axis=1
            )
        else:
            # Sicherstellen dass es boolean ist
            df["dashboard_valid"] = df["dashboard_valid"].astype(bool)

        return df

    def _compute_kpis(self, valid_df: pd.DataFrame, all_df: pd.DataFrame) -> dict:
        """Berechnet die Dashboard-KPIs basierend auf validen Daten."""
        if valid_df.empty:
            return {
                "valid_trades_count": 0,
                "gate_passed_count": 0,
                "profile_count": 0,
                "buy_quote": 0.0,
                "avg_score": 0.0,
            }

        gate_passed = valid_df[valid_df["gate_status"].astype(str).str.upper() == "PASS"].shape[0]
        
        # Profile: Anzahl der erfolgreich aufgelösten Profile im aktuellen Scope (alle Trades)
        profiles = all_df[all_df["profile_status"].astype(str).str.upper() == "FETCHED"]["company_key"].nunique()
        
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

    def _compute_diagnostics(self, all_df: pd.DataFrame, valid_df: pd.DataFrame, invalid_df: pd.DataFrame, filters: dict) -> dict:
        """Berechnet Diagnosewerte und Gründe für fehlende Daten."""
        
        unresolved_sector_count = 0
        missing_sector_count = 0
        missing_price_count = 0
        missing_qty_count = 0
        unknown_direction_count = 0
        
        if not invalid_df.empty:
            # Sektor Diagnose
            if "sector_resolution_status" in invalid_df.columns:
                unresolved_sector_count = invalid_df[invalid_df["sector_resolution_status"] == "UNRESOLVED"].shape[0]
            
            # Fehlende Sektoren (None, Empty, Unknown, N/A)
            sector_vals = invalid_df["sector"].astype(str).str.lower()
            missing_sector_count = invalid_df[
                (invalid_df["sector"].isna()) | 
                (sector_vals.isin(["", "none", "unknown", "n/a"]))
            ].shape[0]
            
            # Preis/Menge
            if "price" in invalid_df.columns:
                missing_price_count = invalid_df[(invalid_df["price"].isna()) | (invalid_df["price"] <= 0)].shape[0]
            if "qty" in invalid_df.columns:
                missing_qty_count = invalid_df[(invalid_df["qty"].isna()) | (invalid_df["qty"] <= 0)].shape[0]
                
            # Richtung
            unknown_direction_count = invalid_df[invalid_df["direction"] == "UNKNOWN"].shape[0]

        # Empty/Warning Reasons
        empty_reason = None
        warning_reason = None
        
        if all_df.empty:
            date_from = filters.get("date_from")
            date_to = filters.get("date_to")
            
            # Variante B: Zusatzdiagnose Zeitbereich in DB
            extreme_dates = self.trade_repo.get_extreme_dates()
            db_min = extreme_dates.get("min_date")
            db_max = extreme_dates.get("max_date")
            
            if date_from and date_to:
                empty_reason = f"Im Zeitraum {date_from} bis {date_to} wurden keine Trades gefunden."
                if db_min and db_max:
                    empty_reason += f" In der Datenbank sind jedoch Trades vom {db_min} bis {db_max} vorhanden."
            else:
                empty_reason = "Keine Trades im aktuellen Scope gefunden."
                if db_min and db_max:
                    empty_reason += f" Die Datenbank enthält Trades im Zeitraum {db_min} bis {db_max}."
        elif valid_df.empty:
            warning_reason = "Im aktuellen Scope sind Trades vorhanden, aber keine für das Dashboard validen Datensätze."
            if unresolved_sector_count > 0 or missing_sector_count > 0:
                warning_reason += " Häufigste Ursache: fehlende oder unresolved Sektorauflösung."
            elif missing_price_count > 0 or missing_qty_count > 0:
                warning_reason += " Häufigste Ursache: fehlende Preis- oder Mengeninformationen."

        return {
            "scoped_trades_count": all_df.shape[0],
            "invalid_trades_count": invalid_df.shape[0],
            "unresolved_sector_count": unresolved_sector_count,
            "missing_sector_count": missing_sector_count,
            "missing_price_count": missing_price_count,
            "missing_qty_count": missing_qty_count,
            "unknown_direction_count": unknown_direction_count,
            "dashboard_empty_reason": empty_reason,
            "dashboard_warning_reason": warning_reason
        }

    def _prepare_charts(self, valid_df: pd.DataFrame) -> dict:
        """Bereitet Daten für die Diagramme vor."""
        charts = {
            "sector_distribution_buy": pd.DataFrame(),
            "sector_distribution_sell": pd.DataFrame(),
            "timeline_distribution": pd.DataFrame(),
        }
        
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
