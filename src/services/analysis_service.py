"""Analyse-Service für UI-taugliche Aggregationen."""

from __future__ import annotations

import pandas as pd

from src.db.mysql_repository import CompanyMySqlRepository, InsiderTradeMySqlRepository
from src.models.analysis_result import AnalysisResult
from src.services.accumulation_service import AccumulationService

# Fachliche Score-Konstanten (Gewichtungen in Prozent)
SCORE_WEIGHT_TRADE_VALUE = 0.35
SCORE_WEIGHT_DIRECTION = 0.20
SCORE_WEIGHT_MARKET_CAP = 0.15
SCORE_WEIGHT_MARKET_VALIDITY = 0.15
SCORE_WEIGHT_INSIDER_ROLE = 0.15

# Score-Klassen-Grenzen (0-100 Skala)
SCORE_CLASS_A = 80  # >= 80
SCORE_CLASS_B = 60  # 60-79
SCORE_CLASS_C = 40  # 40-59
SCORE_CLASS_D = 20  # 20-39
# CLASS_E: < 20

def _classify_score(score: float | None) -> str | None:
    """Weist einen numerischen Score einer fachlichen Klasse A-E zu."""
    if score is None:
        return None
    if score >= SCORE_CLASS_A:
        return "A"
    elif score >= SCORE_CLASS_B:
        return "B"
    elif score >= SCORE_CLASS_C:
        return "C"
    elif score >= SCORE_CLASS_D:
        return "D"
    else:
        return "E"


class AnalysisService:
    """Bereitet Trade- und Unternehmensdaten für Explorer und Ticker-Details auf."""

    def __init__(
        self,
        trade_repo: InsiderTradeMySqlRepository,
        company_repo: CompanyMySqlRepository,
    ) -> None:
        self.trade_repo = trade_repo
        self.company_repo = company_repo

    def compute_trade_score(self, trade: dict | pd.Series) -> tuple[float, str | None]:
        """Berechnet den Gesamtscore für einen Trade basierend auf 5 Dimensionen.

        Dimensionen:
        - Trade Value (35%): Normalisiert auf [0..1] basierend auf Wertspanne (100k-10M)
        - Direction (20%): KAUF +1, VERKAUF +0.5
        - MarketCap (15%): Normalisiert auf [0..1] basierend auf Marktkap-Spanne (100M-500B)
        - Market Validity (15%): Prüft auf ungültige Preise, fehlende Profildaten
        - Insider Role (15%): Officer/Director +1, Sonstiges +0.5 (Heuristik aus type_of_owner)

        Returns:
            Tuple (score_value [0-100], score_class [A-E])
        """
        try:
            # Extraktion fachlicher Felder mit defensiven Defaults
            trade_value = float(trade.get("trade_value_estimated") or 0)
            direction_raw = str(trade.get("direction") or trade.get("acquisition_or_disposition") or "").upper()
            direction = "A" if direction_raw in {"A", "BUY"} else "D" if direction_raw in {"D", "SELL"} else ""
            market_cap = float(trade.get("market_cap") or 0)
            validation_status = str(trade.get("validation_status") or "VALID").upper()
            type_of_owner = str(trade.get("type_of_owner") or "").lower()
            profile_status = str(trade.get("profile_status") or "NOT_REQUESTED").upper()

            # 1. Trade Value Score (35%)
            min_value, max_value = 100_000, 10_000_000
            trade_value_score = min(1.0, max(0.0, (trade_value - min_value) / (max_value - min_value)))

            # 2. Direction Score (20%)
            direction_score = 1.0 if direction == "A" else (0.5 if direction == "D" else 0.0)

            # 3. MarketCap Score (15%)
            min_mcap, max_mcap = 100_000_000, 500_000_000_000
            market_cap_score = min(1.0, max(0.0, (market_cap - min_mcap) / (max_mcap - min_mcap)))

            # 4. Market Validity Score (15%)
            validity_score = 0.0
            if validation_status == "VALID":
                validity_score += 0.5
            if profile_status == "FETCHED":
                validity_score += 0.5
            validity_score = min(1.0, validity_score)

            # 5. Insider Role Score (15%)
            role_score = 0.0
            if "officer" in type_of_owner or "director" in type_of_owner or "ceo" in type_of_owner or "cfo" in type_of_owner:
                role_score = 1.0
            else:
                role_score = 0.5

            # Gewichtete Aggregation: 0-100
            score_value = (
                trade_value_score * SCORE_WEIGHT_TRADE_VALUE +
                direction_score * SCORE_WEIGHT_DIRECTION +
                market_cap_score * SCORE_WEIGHT_MARKET_CAP +
                validity_score * SCORE_WEIGHT_MARKET_VALIDITY +
                role_score * SCORE_WEIGHT_INSIDER_ROLE
            ) * 100
            score_value = round(float(score_value), 2)
            score_class = _classify_score(score_value)
            return score_value, score_class
        except (TypeError, ValueError, KeyError, AttributeError):
            return 0.0, None

    def _ensure_trade_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalisiert UI-relevante Pflichtfelder defensiv für Explorer und Detailansicht."""
        if df.empty:
            empty = df.copy()
            for col in [
                "score",
                "score_class",
                "direction",
                "qty",
                "price",
                "trade_value_estimated",
                "market_cap",
            ]:
                if col not in empty.columns:
                    empty[col] = pd.NA
            return empty

        normalized = df.copy()

        # Alias/Fallback-Felder harmonisieren.
        if "qty" not in normalized.columns and "securities_transacted" in normalized.columns:
            normalized["qty"] = normalized["securities_transacted"]
        if "score" not in normalized.columns and "score_value" in normalized.columns:
            normalized["score"] = normalized["score_value"]

        for numeric_col in ["score", "qty", "price", "trade_value_estimated", "market_cap"]:
            if numeric_col not in normalized.columns:
                normalized[numeric_col] = pd.NA
            normalized[numeric_col] = pd.to_numeric(normalized[numeric_col], errors="coerce")

        if "direction" not in normalized.columns:
            normalized["direction"] = pd.NA
        if "acquisition_or_disposition" in normalized.columns:
            aod = normalized["acquisition_or_disposition"].fillna("").astype(str).str.strip().str.upper()
            mapped = aod.map({"A": "BUY", "BUY": "BUY", "D": "SELL", "SELL": "SELL"})
            normalized["direction"] = mapped.fillna(normalized["direction"])
        normalized["direction"] = (
            normalized["direction"].fillna("UNKNOWN").astype(str).str.strip().str.upper().replace({"": "UNKNOWN", "A": "BUY", "D": "SELL"})
        )

        missing_value_mask = normalized["trade_value_estimated"].isna() & normalized["qty"].notna() & normalized["price"].notna()
        normalized.loc[missing_value_mask, "trade_value_estimated"] = (
            normalized.loc[missing_value_mask, "qty"] * normalized.loc[missing_value_mask, "price"]
        )

        if "score_class" not in normalized.columns:
            normalized["score_class"] = pd.NA

        score_missing_mask = normalized["score"].isna()
        if score_missing_mask.any():
            computed = normalized.loc[score_missing_mask].apply(
                lambda row: pd.Series(self.compute_trade_score(row), index=["score", "score_class"]),
                axis=1,
            )
            normalized.loc[score_missing_mask, "score"] = pd.to_numeric(computed["score"], errors="coerce")
            normalized.loc[score_missing_mask, "score_class"] = computed["score_class"]

        class_missing_mask = normalized["score_class"].isna() | (normalized["score_class"].astype(str).str.strip() == "")
        normalized.loc[class_missing_mask, "score_class"] = normalized.loc[class_missing_mask, "score"].apply(_classify_score)

        normalized["score"] = pd.to_numeric(normalized["score"], errors="coerce")
        normalized["score_class"] = normalized["score_class"].where(normalized["score_class"].notna(), None)
        return normalized

    def get_filtered_trades(
        self, 
        filters: dict | None = None, 
        limit: int = 500,
        accumulate: bool = True,
        min_value: float = 0
    ) -> pd.DataFrame:
        """Lädt bereinigte Trades mit optionalen Filtern und Akkumulation."""
        df = self.trade_repo.fetch_trades(filters=filters, limit=limit)
        df = self._ensure_trade_columns(df)

        if df.empty:
            return df

        # Invariante A & F sicherstellen: Filter auf Rohdaten vor Aggregation
        if min_value > 0:
            df = df[df["trade_value_estimated"] >= min_value]

        if accumulate and not df.empty:
            try:
                return AccumulationService.accumulate_trades(df)
            except Exception:
                return df

        return df

    def get_ticker_detail(self, company_key: str, accumulate: bool = True) -> AnalysisResult:
        """Liefert Profil, letzte Trades und Basiskennzahlen für einen Company-Key."""
        trades = self.trade_repo.fetch_trades(filters={"company_key": company_key}, limit=500)
        trades = self._ensure_trade_columns(trades)
        profile_df = self.company_repo.fetch_company(company_key)

        can_accumulate = False
        if not trades.empty and "transaction_date" in trades.columns:
            parsed_dates = pd.to_datetime(trades["transaction_date"], errors="coerce")
            can_accumulate = parsed_dates.notna().any()
            if can_accumulate:
                trades = trades.copy()
                trades["transaction_date"] = parsed_dates
                try:
                    trades = AccumulationService.tag_trades_with_groups(trades)
                    trades = self._ensure_trade_columns(trades)
                except Exception:
                    can_accumulate = False

        if accumulate and not trades.empty and can_accumulate:
            try:
                display_trades = AccumulationService.accumulate_trades(trades)
            except Exception:
                display_trades = trades
        else:
            display_trades = trades

        display_trades = self._ensure_trade_columns(display_trades)

        metrics = {
            "trade_count": int(len(trades)),
            "avg_price": float(trades["price"].dropna().mean()) if (not trades.empty and "price" in trades.columns and not trades["price"].dropna().empty) else None,
            "total_qty": float(trades["qty"].dropna().sum()) if (not trades.empty and "qty" in trades.columns and not trades["qty"].dropna().empty) else None,
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
