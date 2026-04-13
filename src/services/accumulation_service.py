"""Service zur Akkumulation von Insider-Trades nach fachlichen Regeln."""

from __future__ import annotations

import pandas as pd
import numpy as np


class AccumulationService:
    """Aggregiert Trades basierend auf Person, Firma, Richtung und Zeitnähe."""

    @staticmethod
    def tag_trades_with_groups(df: pd.DataFrame, window_days: int = 3) -> pd.DataFrame:
        """Ordnet jedem Trade eine accumulation_group_id basierend auf 3-Tage-Fenster zu."""
        if df.empty:
            return df

        # Kopie erstellen
        working_df = df.copy()

        # Fachliche Ausschlüsse: Preis-invalid Trades werden nicht akkumuliert.
        if "validation_status" in working_df.columns:
            working_df = working_df[working_df["validation_status"].fillna("VALID") != "PRICE_INVALID"].copy()
        if working_df.empty:
            return working_df

        # Fachliche Gruppierung strikt nach Symbol/Person/Richtung/Security/TransactionType.
        working_df["_group_symbol"] = (
            working_df.get("symbol_at_trade", working_df.get("symbol", pd.Series(index=working_df.index)))
            .fillna("")
            .astype(str)
            .str.upper()
        )
        working_df["_group_reporting"] = working_df.get("reporting_name", pd.Series(index=working_df.index)).fillna("Unknown").astype(str)
        working_df["_group_aod"] = working_df.get("acquisition_or_disposition", pd.Series(index=working_df.index)).fillna("").astype(str)
        working_df["_group_security"] = working_df.get("security_name", pd.Series(index=working_df.index)).fillna("").astype(str)
        working_df["_group_tx_type"] = working_df.get("transaction_type", pd.Series(index=working_df.index)).fillna("").astype(str)

        # Sicherstellen, dass Datentypen passen
        working_df["transaction_date"] = pd.to_datetime(working_df["transaction_date"])

        # Sortieren für die Lückenerkennung
        sort_cols = ["_group_symbol", "_group_reporting", "_group_aod", "_group_security", "_group_tx_type", "transaction_date"]
        working_df = working_df.sort_values(sort_cols)

        # Fachliche Gruppe (ohne Zeit)
        tech_group_cols = ["_group_symbol", "_group_reporting", "_group_aod", "_group_security", "_group_tx_type"]

        # Markiere Zeilen, die eine neue fachliche Gruppe beginnen
        # Da NaN != NaN in Pandas True ist, fillna() nutzen für stabilen Vergleich
        temp_compare = working_df[tech_group_cols].fillna("N/A")
        is_new_tech_group = (temp_compare != temp_compare.shift()).any(axis=1)

        # Berechne Zeitdifferenz zum Vorgänger innerhalb der (potenziellen) Gruppe
        date_diff = working_df["transaction_date"].diff()
        # 3-Tage-Fenster: Wenn Zeitlücke > 3 Tage, neue Gruppe
        is_too_far = date_diff > pd.Timedelta(days=window_days)

        # Eine neue finale Gruppe beginnt bei neuer tech_group ODER zu großer Zeitlücke
        is_new_group = is_new_tech_group | is_too_far

        # Akkumulations-ID vergeben (einfacher Counter)
        working_df["accumulation_group_id"] = is_new_group.cumsum().astype(str)
        return working_df

    @staticmethod
    def accumulate_trades(df: pd.DataFrame, window_days: int = 3) -> pd.DataFrame:
        """
        Gruppiert Trades zu 3-Tage-Aggregaten mit Score-Durchschnitten.
        """
        if df.empty:
            return df

        working_df = AccumulationService.tag_trades_with_groups(df, window_days)

        # Aggregation definieren
        agg_funcs = {
            "transaction_date": ["min", "max", "count"],
            "qty": "sum",
            "trade_value_estimated": "sum",
            "price": "mean",
            "score": "mean",
            "symbol_at_trade": "first",
            "company_name": "first",
            "reporting_name": "first",
            "type_of_owner": "first",
            "acquisition_or_disposition": "first",
            "security_name": "first",
            "transaction_type": "first",
            "reporting_cik": "first",
            "company_cik": "first",
            "company_key": "first",
            "gate_status": "first",
            "validation_status": "first",
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
