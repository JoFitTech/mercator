"""Service zur Akkumulation von Insider-Trades nach fachlichen Regeln."""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import timedelta
from typing import Any


class AccumulationService:
    """Aggregiert Trades basierend auf Person, Firma, Richtung und Zeitnähe."""

    @staticmethod
    def tag_trades_with_groups(df: pd.DataFrame, max_gap_days: int = 1) -> pd.DataFrame:
        """Ordnet jedem Trade eine accumulation_group_id zu."""
        if df.empty:
            return df

        # Kopie erstellen
        working_df = df.copy()
        
        # Hilfsfelder für Gruppierung (Fallbacks)
        person_col = "reporting_cik" if "reporting_cik" in working_df.columns else "reporting_name"
        company_col = "company_cik" if "company_cik" in working_df.columns else "symbol_at_trade"
        
        working_df["_group_person"] = working_df[person_col].fillna(working_df["reporting_name"]).fillna("Unknown")
        working_df["_group_company"] = working_df[company_col].fillna(working_df["symbol_at_trade"]).fillna("Unknown")
        
        # Sicherstellen, dass Datentypen passen
        working_df["transaction_date"] = pd.to_datetime(working_df["transaction_date"])
        
        # Sortieren für die Lückenerkennung
        sort_cols = ["_group_person", "_group_company", "acquisition_or_disposition", "security_name", "transaction_date"]
        working_df = working_df.sort_values(sort_cols)

        # Fachliche Gruppe (ohne Zeit)
        tech_group_cols = ["_group_person", "_group_company", "acquisition_or_disposition", "security_name"]
        
        # Markiere Zeilen, die eine neue fachliche Gruppe beginnen
        # Da NaN != NaN in Pandas True ist, fillna() nutzen für stabilen Vergleich
        temp_compare = working_df[tech_group_cols].fillna("N/A")
        is_new_tech_group = (temp_compare != temp_compare.shift()).any(axis=1)
        
        # Berechne Zeitdifferenz zum Vorgänger innerhalb der (potenziellen) Gruppe
        date_diff = working_df["transaction_date"].diff()
        is_too_far = date_diff > pd.Timedelta(days=max_gap_days)
        
        # Eine neue finale Gruppe beginnt bei neuer tech_group ODER zu großer Zeitlücke
        is_new_group = is_new_tech_group | is_too_far
        
        # Akkumulations-ID vergeben (einfacher Counter)
        working_df["accumulation_group_id"] = is_new_group.cumsum().astype(str)
        return working_df

    @staticmethod
    def accumulate_trades(df: pd.DataFrame, max_gap_days: int = 1) -> pd.DataFrame:
        """
        Gruppiert Trades zu Aggregaten.
        """
        if df.empty:
            return df

        working_df = AccumulationService.tag_trades_with_groups(df, max_gap_days)
        
        # Aggregation definieren
        agg_funcs = {
            "transaction_date": ["min", "max", "count"],
            "qty": "sum",
            "trade_value_estimated": "sum",
            "price": "mean",
            "symbol_at_trade": "first",
            "company_name": "first",
            "reporting_name": "first",
            "type_of_owner": "first",
            "acquisition_or_disposition": "first",
            "security_name": "first",
            "reporting_cik": "first",
            "company_cik": "first",
            "company_key": "first",
            "gate_status": "first",
            "filing_date": "max",
            "source_url": "first"
        }
        
        existing_agg_cols = {k: v for k, v in agg_funcs.items() if k in working_df.columns}
        grouped = working_df.groupby("accumulation_group_id").agg(existing_agg_cols)
        
        # Flatten MultiIndex Columns
        grouped.columns = [f"{col}_{stat}" if stat not in ["first", "sum"] else col for col, stat in grouped.columns]
        
        # Umbenennungen für MVP-Schema
        grouped = grouped.rename(columns={
            "transaction_date_min": "accumulation_start_date",
            "transaction_date_max": "accumulation_end_date",
            "transaction_date_count": "accumulated_trade_count",
            "qty": "accumulated_qty",
            "trade_value_estimated": "accumulated_trade_value_estimated",
            "filing_date_max": "filing_date"
        })
        
        grouped["is_accumulated"] = grouped["accumulated_trade_count"] > 1
        
        # Gewichteter Durchschnittspreis
        grouped["accumulated_avg_price_weighted"] = np.where(
            grouped["accumulated_qty"] > 0,
            grouped["accumulated_trade_value_estimated"] / grouped["accumulated_qty"],
            grouped["price_mean"]
        )
        
        # Prüfe, ob mehrere Preise enthalten sind
        price_std = working_df.groupby("accumulation_group_id")["price"].std()
        grouped["contains_multiple_prices"] = (price_std > 0.001).fillna(False)
        
        grouped["transaction_date"] = grouped["accumulation_start_date"]
        
        # Richtung mappen
        grouped["direction"] = grouped["acquisition_or_disposition"].apply(
            lambda x: "BUY" if x == "A" else ("SELL" if x == "D" else "UNKNOWN")
        )
        
        grouped = grouped.sort_values("accumulation_start_date", ascending=False)
        return grouped.reset_index()

    @staticmethod
    def get_trades_for_group(df: pd.DataFrame, group_id: str) -> pd.DataFrame:
        """Gibt alle Einzeltrades einer Akkumulationsgruppe zurück."""
        if "accumulation_group_id" not in df.columns:
            # Falls noch nicht getagged, taggen wir jetzt (aber das ist suboptimal)
            df = AccumulationService.tag_trades_with_groups(df)
            
        return df[df["accumulation_group_id"] == group_id].sort_values("transaction_date", ascending=False)
