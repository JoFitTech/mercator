"""Analyse-Service für UI-taugliche Aggregationen."""

from __future__ import annotations

import logging
import pandas as pd

from src.data_sources.fmp_client import FmpClient
from src.db.mysql_repository import CompanyMySqlRepository, InsiderTradeMySqlRepository
from src.domain_rules import ScoreGatePolicy, classify_score, normalize_symbol, sanitize_symbol_options
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
LOGGER = logging.getLogger(__name__)

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
        score_gate_policy: ScoreGatePolicy | None = None,
        fmp_client: FmpClient | None = None,
    ) -> None:
        self.trade_repo = trade_repo
        self.company_repo = company_repo
        self.score_gate_policy = score_gate_policy or ScoreGatePolicy()
        self.fmp_client = fmp_client

    def list_ticker_options(self) -> list[str]:
        """Liefert ausschließlich symbolbasierte, bereinigte Tickeroptionen.

        Fokussiert auf Ticker, für die tatsächlich Trades in der MySQL-Datenbank vorliegen.
        """

        symbols = self.trade_repo.fetch_all_symbols()
        return sanitize_symbol_options(symbols)

    @staticmethod
    def _to_profile_view_model(profile: dict) -> dict:
        """Mappt DB/API-Felder konsistent in die UI-Profilansicht."""

        return {
            "symbol": profile.get("current_symbol") or profile.get("symbol"),
            "company_name": profile.get("company_name") or profile.get("companyName"),
            "market_cap": profile.get("market_cap") or profile.get("mktCap"),
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "country": profile.get("country"),
            "exchange_full_name": profile.get("exchange_full_name") or profile.get("exchangeFullName") or profile.get("exchange"),
            "description": profile.get("description"),
            "isin": profile.get("isin"),
            "cik": profile.get("company_cik") or profile.get("cik"),
            "ceo": profile.get("ceo"),
            "full_time_employees": profile.get("full_time_employees") or profile.get("fullTimeEmployees"),
            "currency": profile.get("currency") or "USD",
            "website": profile.get("website"),
        }

    def _load_or_fetch_company_profile(self, symbol: str) -> tuple[dict, str]:
        normalized_symbol = normalize_symbol(symbol)
        if not normalized_symbol:
            LOGGER.warning("Company lookup übersprungen: ungültiges Symbol `%s`", symbol)
            return {}, "invalid_symbol"

        profile = self.company_repo.get_company_by_current_symbol(normalized_symbol)
        if profile:
            LOGGER.info("Company lookup symbol=%s source=mysql", normalized_symbol)
            return self._to_profile_view_model(profile), "mysql"

        LOGGER.info("Company lookup symbol=%s source=mysql_miss", normalized_symbol)
        if self.fmp_client is None:
            LOGGER.warning("Company lookup symbol=%s ohne API2-Fallback (FMP-Client fehlt)", normalized_symbol)
            return {}, "no_api2"

        try:
            api_profile = self.fmp_client.fetch_company_profile(normalized_symbol)
            if not api_profile:
                LOGGER.warning("Company lookup symbol=%s API2 lieferte leere Antwort", normalized_symbol)
                return {}, "api2_empty"
            # Root-cause-Fix: Detailansicht brach bei Stub-Profilen ab. Bei MySQL-Miss
            # laden wir jetzt symbolbasiert nach und persistieren sofort im Clean-Store.
            company_payload = {
                "company_key": f"SYM:{normalized_symbol}",
                "company_cik": api_profile.get("cik"),
                "current_symbol": normalize_symbol(api_profile.get("symbol")) or normalized_symbol,
                "company_name": api_profile.get("companyName"),
                "profile_status": "FETCHED",
                "profile_reason": None,
                "market_cap": api_profile.get("mktCap"),
                "currency": api_profile.get("currency"),
                "isin": api_profile.get("isin"),
                "exchange": api_profile.get("exchangeShortName") or api_profile.get("exchange"),
                "exchange_full_name": api_profile.get("exchangeFullName") or api_profile.get("exchange"),
                "industry": api_profile.get("industry"),
                "sector": api_profile.get("sector"),
                "country": api_profile.get("country"),
                "website": api_profile.get("website"),
                "description": api_profile.get("description"),
                "ceo": api_profile.get("ceo"),
                "full_time_employees": api_profile.get("fullTimeEmployees"),
            }
            self.company_repo.upsert_company(company_payload)
            LOGGER.info("Company lookup symbol=%s source=api2_fetched", normalized_symbol)
            return self._to_profile_view_model(company_payload | api_profile), "api2"
        except Exception:
            LOGGER.exception("Company lookup symbol=%s API2-Fallback fehlgeschlagen", normalized_symbol)
            return {}, "api2_failed"

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
        normalized["score_status"] = normalized["score"].apply(lambda v: classify_score(v, self.score_gate_policy)[0])
        normalized["score_status_color"] = normalized["score"].apply(lambda v: classify_score(v, self.score_gate_policy)[1])
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

    def get_ticker_detail(self, symbol: str, accumulate: bool = True) -> AnalysisResult:
        """Liefert Profil, letzte Trades und Basiskennzahlen für ein Symbol."""
        normalized_symbol = normalize_symbol(symbol)
        if not normalized_symbol:
            return AnalysisResult(title="Ticker-Detail", note="Ungültiges Symbol.")

        trades = self.trade_repo.fetch_trades(filters={"symbol": normalized_symbol}, limit=500)
        if trades.empty:
            # Fallback nur auf SYM, nicht auf CIK für die Symbol-Detailansicht
            trades = self.trade_repo.fetch_trades(filters={"company_key": f"SYM:{normalized_symbol}"}, limit=500)

        trades = self._ensure_trade_columns(trades)

        # Gate-Analyse für Enrichment-Regel und UI-Status
        gate_statuses = set()
        if not trades.empty and "gate_status" in trades.columns:
            gate_statuses = set(trades["gate_status"].fillna("").astype(str).str.upper().unique())

        # Fachregel: Company Context nur für PASS und HOLD (PENDING), nicht für FAIL
        company_context_allowed = any(s in {"PASS", "PENDING"} for s in gate_statuses)

        if company_context_allowed:
            profile, profile_source = self._load_or_fetch_company_profile(normalized_symbol)
        else:
            profile, profile_source = {}, "fail_excluded" if not trades.empty else "no_trades"

        # Bestimmung des Gesamtstatus für die UI-Visualisierung
        overall_status = "FAIL"
        if "PASS" in gate_statuses:
            overall_status = "PASS"
        elif "PENDING" in gate_statuses:
            overall_status = "HOLD"

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
            "overall_status": overall_status,
            "can_enrich": company_context_allowed,
        }
        rows = display_trades.to_dict(orient="records")
        # Rohdaten mit Group-ID mitschicken
        raw_rows = trades.to_dict(orient="records")
        
        note = "Profildaten verfügbar." if profile else "Unternehmensprofil derzeit nicht verfügbar"
        if not profile:
            LOGGER.warning("Company lookup symbol=%s blieb leer source=%s", normalized_symbol, profile_source)
        
        return AnalysisResult(
            title=f"Ticker-Detail {normalized_symbol}",
            metrics=metrics,
            rows=rows,
            raw_rows=raw_rows,
            company_profile=profile,
            note=note,
        )
