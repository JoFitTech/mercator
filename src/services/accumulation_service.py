"""Service zur Akkumulation von Insider-Trades nach fachlichen Regeln."""

from __future__ import annotations

import pandas as pd
import numpy as np


def _classify_score(score: float | None) -> str | None:
    """Leitet die vorhandenen Score-Klassen A-E aus einem numerischen Score ab."""
    if score is None or pd.isna(score):
        return None
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "E"


def _normalize_direction(value: object) -> str:
    normalized = str(value or "").strip().upper()
    if normalized in {"A", "BUY"}:
        return "BUY"
    if normalized in {"D", "SELL"}:
        return "SELL"
    return "UNKNOWN"


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

        if "transaction_date" not in working_df.columns:
            return working_df

        # Sicherstellen, dass Datentypen passen
        working_df["transaction_date"] = pd.to_datetime(working_df["transaction_date"], errors="coerce")
        working_df = working_df.dropna(subset=["transaction_date"]).copy()
        if working_df.empty:
            return working_df

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
            return pd.DataFrame(
                columns=[
                    "accumulation_group_id",
                    "transaction_date",
                    "accumulation_start_date",
                    "accumulation_end_date",
                    "accumulated_trade_count",
                    "accumulated_qty",
                    "accumulated_trade_value_estimated",
                    "accumulated_avg_price_weighted",
                    "score",
                    "score_class",
                    "direction",
                ]
            )

        working_df = df.copy()
        if "qty" not in working_df.columns and "securities_transacted" in working_df.columns:
            working_df["qty"] = working_df["securities_transacted"]

        for numeric_col in ["qty", "trade_value_estimated", "price", "score"]:
            if numeric_col not in working_df.columns:
                working_df[numeric_col] = np.nan
            working_df[numeric_col] = pd.to_numeric(working_df[numeric_col], errors="coerce")

        if "acquisition_or_disposition" not in working_df.columns:
            working_df["acquisition_or_disposition"] = ""
        working_df["acquisition_or_disposition"] = working_df["acquisition_or_disposition"].fillna("").astype(str).str.upper()

        working_df = AccumulationService.tag_trades_with_groups(working_df, window_days)
        if working_df.empty or "accumulation_group_id" not in working_df.columns:
            return pd.DataFrame(
                columns=[
                    "accumulation_group_id",
                    "transaction_date",
                    "accumulation_start_date",
                    "accumulation_end_date",
                    "accumulated_trade_count",
                    "accumulated_qty",
                    "accumulated_trade_value_estimated",
                    "accumulated_avg_price_weighted",
                    "score",
                    "score_class",
                    "direction",
                ]
            )

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
        grouped.columns = [
            "score" if (col == "score" and stat == "mean") else (f"{col}_{stat}" if stat not in ["first", "sum"] else col)
            for col, stat in grouped.columns
        ]

        # Umbenennungen für MVP-Schema
        grouped = grouped.rename(columns={
            "transaction_date_min": "accumulation_start_date",
            "transaction_date_max": "accumulation_end_date",
            "transaction_date_count": "accumulated_trade_count",
            "qty": "accumulated_qty",
            "trade_value_estimated": "accumulated_trade_value_estimated",
            "filing_date_max": "filing_date"
        })

        if "accumulated_trade_count" not in grouped.columns:
            grouped["accumulated_trade_count"] = 1

        grouped["is_accumulated"] = grouped["accumulated_trade_count"] > 1

        # Gewichteter Durchschnittspreis
        if "accumulated_qty" not in grouped.columns:
            grouped["accumulated_qty"] = np.nan
        if "accumulated_trade_value_estimated" not in grouped.columns:
            grouped["accumulated_trade_value_estimated"] = np.nan
        if "price_mean" not in grouped.columns:
            grouped["price_mean"] = np.nan

        grouped["accumulated_avg_price_weighted"] = np.where(
            grouped["accumulated_qty"].fillna(0) > 0,
            grouped["accumulated_trade_value_estimated"] / grouped["accumulated_qty"],
            grouped["price_mean"],
        )

        # Prüfe, ob mehrere Preise enthalten sind
        if "price" in working_df.columns:
            price_std = working_df.groupby("accumulation_group_id")["price"].std()
            grouped["contains_multiple_prices"] = (price_std > 0.001).fillna(False)
        else:
            grouped["contains_multiple_prices"] = False

        grouped["transaction_date"] = grouped.get("accumulation_start_date", pd.NaT)

        if "score" not in grouped.columns:
            grouped["score"] = np.nan
        grouped["score"] = pd.to_numeric(grouped["score"], errors="coerce")
        grouped["score_class"] = grouped["score"].apply(_classify_score)

        # Richtung mappen
        if "acquisition_or_disposition" not in grouped.columns:
            grouped["acquisition_or_disposition"] = ""
        grouped["direction"] = grouped["acquisition_or_disposition"].apply(_normalize_direction)

        sort_col = "accumulation_start_date" if "accumulation_start_date" in grouped.columns else "transaction_date"
        grouped = grouped.sort_values(sort_col, ascending=False)
        return grouped.reset_index()

    @staticmethod
    def get_trades_for_group(df: pd.DataFrame, group_id: str) -> pd.DataFrame:
        """Gibt alle Einzeltrades einer Akkumulationsgruppe zurück."""
        if "accumulation_group_id" not in df.columns:
            # Falls noch nicht getagged, taggen wir jetzt (aber das ist suboptimal)
            df = AccumulationService.tag_trades_with_groups(df)
            
        return df[df["accumulation_group_id"] == group_id].sort_values("transaction_date", ascending=False)
