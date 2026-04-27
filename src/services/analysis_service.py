"""Analyse-Service für UI-taugliche Aggregationen."""

from __future__ import annotations

import logging
import time
import json
import pandas as pd

from src.data_sources.fmp_client import FmpClient
from src.db.repositories.company_repository import CompanyMySqlRepository
from src.db.repositories.trade_repository import InsiderTradeMySqlRepository
from src.domain_rules import (
    ScoreGatePolicy,
    normalize_symbol,
    sanitize_symbol_options,
)
from src.services.scoring_service import ScoringService
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
        scoring_service: ScoringService | None = None,
    ) -> None:
        self.trade_repo = trade_repo
        self.company_repo = company_repo
        self.score_gate_policy = score_gate_policy or ScoreGatePolicy()
        self.fmp_client = fmp_client
        self.scoring_service = scoring_service or ScoringService(self.score_gate_policy)

    # TTL-Cache für ticker_options (DB-Abfrage, teuer)
    _ticker_options_cache: tuple[float, list[str]] | None = None
    _TICKER_CACHE_TTL = 60.0  # Sekunden
    _trades_page_cache: dict[str, tuple[float, tuple[pd.DataFrame, int]]] = {}
    _TRADES_PAGE_CACHE_TTL = 20.0  # Sekunden

    @staticmethod
    def _freeze_filters(filters: dict | None) -> str:
        if not filters:
            return "{}"
        normalized = {str(k): str(v) for k, v in sorted(filters.items(), key=lambda item: str(item[0]))}
        return json.dumps(normalized, ensure_ascii=True, sort_keys=True)

    def list_ticker_options(self) -> list[str]:
        """Liefert ausschließlich symbolbasierte, bereinigte Tickeroptionen.

        Fokussiert auf Ticker, für die tatsächlich Trades in der MySQL-Datenbank vorliegen.
        Ergebnis wird für 60 Sekunden in-process gecacht.
        """
        now = time.monotonic()
        cached = AnalysisService._ticker_options_cache
        if cached is not None and now - cached[0] < AnalysisService._TICKER_CACHE_TTL:
            return cached[1]

        symbols: list[object] = []
        if hasattr(self.trade_repo, "fetch_all_symbols"):
            symbols.extend(self.trade_repo.fetch_all_symbols() or [])
        if hasattr(self.company_repo, "fetch_all_symbols"):
            symbols.extend(self.company_repo.fetch_all_symbols() or [])
        result = sanitize_symbol_options(symbols)
        AnalysisService._ticker_options_cache = (now, result)
        return result

    def get_companies(self, limit: int = 100, offset: int = 0) -> pd.DataFrame:
        """Gibt eine Liste der Unternehmen als DataFrame zurück."""
        companies = self.company_repo.list_companies(limit=limit, offset=offset)
        if not companies:
            return pd.DataFrame()
        return pd.DataFrame(companies)

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
            "trade_republic_universe_status": profile.get("trade_republic_universe_status"),
            "trade_republic_match_method": profile.get("trade_republic_match_method"),
            "trade_republic_match_confidence": profile.get("trade_republic_match_confidence"),
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
        """Berechnet den Gesamtscore für einen Trade basierend auf der diskreten Domain-Logik."""
        res = self.scoring_service.compute_trade_score(trade)
        return res["score"], res["score_class"]

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

        # Vektorisierte Status-Klassifizierung statt teurer row-wise Funktionsaufrufe.
        pass_min = float(self.scoring_service.policy.score_threshold_pass_min)
        hold_min = float(self.scoring_service.policy.score_threshold_hold_min)
        score_series = normalized["score"]
        normalized["score_status"] = self.scoring_service.policy.fail_label
        normalized["score_status_color"] = self.scoring_service.policy.fail_color
        hold_mask = score_series.notna() & (score_series >= hold_min)
        pass_mask = score_series.notna() & (score_series >= pass_min)
        normalized.loc[hold_mask, "score_status"] = self.scoring_service.policy.hold_label
        normalized.loc[hold_mask, "score_status_color"] = self.scoring_service.policy.hold_color
        normalized.loc[pass_mask, "score_status"] = self.scoring_service.policy.pass_label
        normalized.loc[pass_mask, "score_status_color"] = self.scoring_service.policy.pass_color
        if "trade_republic_universe_status" not in normalized.columns:
            normalized["trade_republic_universe_status"] = pd.NA
        if "company_trade_republic_universe_status" in normalized.columns:
            normalized["trade_republic_universe_status"] = (
                normalized["trade_republic_universe_status"]
                .fillna(normalized["company_trade_republic_universe_status"])
            )
        normalized["trade_republic_universe_status"] = (
            normalized["trade_republic_universe_status"]
            .fillna("UNKNOWN")
            .astype(str)
            .str.upper()
            .replace({"": "UNKNOWN"})
        )
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
        tr_filter = str((filters or {}).get("trade_republic_universe_status") or "").strip().upper()
        if tr_filter and tr_filter != "ALL":
            df = df[df["trade_republic_universe_status"] == tr_filter]

        if accumulate and not df.empty:
            if "transaction_date" not in df.columns:
                return df

            parsed_dates = pd.to_datetime(df["transaction_date"], errors="coerce")
            if not parsed_dates.notna().any():
                return df

            try:
                df = df.copy()
                df["transaction_date"] = parsed_dates
                return AccumulationService.accumulate_trades(df)
            except Exception:
                return df

        return df

    def get_filtered_trades_page(
        self,
        filters: dict | None,
        limit: int,
        offset: int,
        min_value: float = 0,
    ) -> tuple[pd.DataFrame, int]:
        effective_filters = dict(filters or {})
        if min_value > 0:
            effective_filters["min_value"] = min_value

        cache_key = f"{self._freeze_filters(effective_filters)}|{int(limit)}|{int(offset)}"
        now = time.monotonic()
        cached = AnalysisService._trades_page_cache.get(cache_key)
        if cached is not None and now - cached[0] < AnalysisService._TRADES_PAGE_CACHE_TTL:
            cached_df, cached_total = cached[1]
            return cached_df.copy(), int(cached_total)

        total_count = self.trade_repo.count_trades(filters=effective_filters)
        if limit > 0 and total_count > 0 and offset >= total_count:
            last_page = max(1, (total_count + limit - 1) // limit)
            offset = (last_page - 1) * limit

        df = self.trade_repo.fetch_trades_page(filters=effective_filters, limit=limit, offset=offset)
        df = self._ensure_trade_columns(df)
        if len(AnalysisService._trades_page_cache) > 200:
            AnalysisService._trades_page_cache.clear()
        AnalysisService._trades_page_cache[cache_key] = (now, (df.copy(), int(total_count)))
        return df, total_count

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

        # Berechnung Durchschnitts-Score
        avg_score = float(trades["score"].dropna().mean()) if (not trades.empty and "score" in trades.columns and not trades["score"].dropna().empty) else 0.0
        score_class = _classify_score(avg_score)

        metrics = {
            "trade_count": int(len(trades)),
            "avg_price": float(trades["price"].dropna().mean()) if (not trades.empty and "price" in trades.columns and not trades["price"].dropna().empty) else None,
            "total_qty": float(trades["qty"].dropna().sum()) if (not trades.empty and "qty" in trades.columns and not trades["qty"].dropna().empty) else None,
            "overall_score": avg_score,
            "score_class": score_class,
            "overall_status": overall_status,
            "can_enrich": company_context_allowed,
        }
        rows = display_trades.to_dict(orient="records")
        # Rohdaten mit Group-ID mitschicken
        raw_rows = trades.to_dict(orient="records")
        
        if profile:
            detail_note = "Profildaten verfügbar."
        elif profile_source == "no_api2":
            detail_note = "Profildaten nicht verfügbar (API2 nicht konfiguriert)."
        else:
            detail_note = f"Quelle: {profile_source}"

        return AnalysisResult(
            title=f"Detail für {normalized_symbol}",
            metrics=metrics,
            rows=rows,
            raw_rows=raw_rows,
            company_profile=profile,
            note=detail_note
        )

    def compute_insider_quality(self, reporting_name: str) -> dict | None:
        """Berechnet Kennzahlen zur Qualität eines Insiders (Requirement 4.4)."""
        if not reporting_name:
            return None
            
        trades = self.trade_repo.fetch_trades(filters={"reporting_name": reporting_name}, limit=1000)
        if trades.empty:
            return None
            
        trades = self._ensure_trade_columns(trades)
        
        # 1. Anzahl historischer Trades
        trade_count = len(trades)
        
        # 2. Durchschnittlicher Score
        avg_score = float(trades["score"].dropna().mean()) if "score" in trades.columns else 0.0
        
        # 3. Anteil Gate PASS
        gate_pass_count = (trades["gate_status"].fillna("").astype(str).str.upper() == "PASS").sum()
        gate_pass_share = gate_pass_count / trade_count if trade_count > 0 else 0.0
        
        # 4. Anteil BUY
        buy_count = (trades["direction"] == "BUY").sum()
        buy_share = buy_count / trade_count if trade_count > 0 else 0.0
        
        # 5. Median Trade Value
        median_value = float(trades["trade_value_estimated"].dropna().median()) if "trade_value_estimated" in trades.columns else 0.0
        
        # 6. Anteil Trades in dashboard-validem Bereich
        valid_count = (trades["dashboard_valid"] == True).sum()
        valid_share = valid_count / trade_count if trade_count > 0 else 0.0
        
        # Insider Quality Score (einfache gewichtete Formel)
        # 40% Avg Score, 30% Gate Pass Share, 20% Valid Share, 10% Buy Share (Kauf ist besserer Indikator)
        quality_score = (
            (avg_score / 100.0) * 0.4 +
            gate_pass_share * 0.3 +
            valid_share * 0.2 +
            buy_share * 0.1
        ) * 100
        
        return {
            "reporting_name": reporting_name,
            "trade_count": trade_count,
            "avg_score": round(avg_score, 2),
            "gate_pass_share": round(gate_pass_share * 100, 1),
            "buy_share": round(buy_share * 100, 1),
            "median_value": round(median_value, 2),
            "valid_share": round(valid_share * 100, 1),
            "quality_score": round(quality_score, 2)
        }
