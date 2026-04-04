"""Import-Service für FMP-Feed, Verarbeitung und Persistenz."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.config.settings import DEFAULT_FEED_LIMIT, DEFAULT_FEED_PAGE
from src.data_sources.fmp_client import FmpClient
from src.db.mongo_repository import CompanyMongoRepository, InsiderTradeMongoRepository
from src.db.mysql_repository import CompanyMySqlRepository, InsiderTradeMySqlRepository
from src.preprocessing.gate_evaluator import (
    GATE_PASS,
    GATE_PROFILE_FETCH_FAILED,
    GATE_PROFILE_FETCHED,
    GateEvaluator,
)
from src.preprocessing.cleaning import normalize_insider_trade

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ImportSummary:
    """Ergebnis eines Importlaufs."""

    fetched_feed_records: int
    inserted_raw_records: int
    upserted_clean_records: int
    fetched_profiles: int


class ImportService:
    """Orchestriert FMP-Import, Gate-Prüfung und DB-Speicherung."""

    def __init__(
        self,
        fmp_client: FmpClient,
        gate_evaluator: GateEvaluator,
        raw_repo: InsiderTradeMongoRepository,
        company_mongo_repo: CompanyMongoRepository,
        trade_mysql_repo: InsiderTradeMySqlRepository,
        company_mysql_repo: CompanyMySqlRepository,
        profile_fetch_statuses: tuple[str, ...] = (GATE_PASS,),
    ) -> None:
        self.fmp_client = fmp_client
        self.gate_evaluator = gate_evaluator
        self.raw_repo = raw_repo
        self.company_mongo_repo = company_mongo_repo
        self.trade_mysql_repo = trade_mysql_repo
        self.company_mysql_repo = company_mysql_repo
        self.profile_fetch_statuses = tuple(status.upper() for status in profile_fetch_statuses)

    def run_hourly_import(
        self,
        page: int = DEFAULT_FEED_PAGE,
        limit: int = DEFAULT_FEED_LIMIT,
        profile_fetch_statuses: tuple[str, ...] | None = None,
    ) -> ImportSummary:
        """Führt einen vollständigen MVP-Importlauf aus."""
        fetched_at = datetime.now(timezone.utc)
        raw_feed = self.fmp_client.fetch_latest_insider_trades(page=page, limit=limit)
        normalized = [normalize_insider_trade(item, fetched_at=fetched_at) for item in raw_feed]
        effective_profile_fetch_statuses = {
            status.upper() for status in (profile_fetch_statuses or self.profile_fetch_statuses)
        }

        for item in normalized:
            decision = self.gate_evaluator.evaluate(item)
            item["gate_status"] = decision.status
            item["gate_reason"] = decision.reason

        inserted_raw = self.raw_repo.upsert_raw_trades(normalized)

        fetched_profiles = 0
        for trade in normalized:
            if trade["gate_status"].upper() not in effective_profile_fetch_statuses or not trade.get("symbol"):
                continue

            symbol = trade["symbol"]
            cached = self.company_mongo_repo.get_recent_profile(
                symbol=symbol,
                ttl_days=self.fmp_client.config.profile_ttl_days,
            )
            if cached:
                trade["gate_status"] = GATE_PROFILE_FETCHED
                continue

            try:
                profile = self.fmp_client.fetch_company_profile(symbol)
            except Exception:
                LOGGER.exception("Profilabruf fehlgeschlagen für %s", symbol)
                trade["gate_status"] = GATE_PROFILE_FETCH_FAILED
                continue

            if not profile:
                trade["gate_status"] = GATE_PROFILE_FETCH_FAILED
                continue

            company = self._normalize_company_profile(profile, fetched_at)
            self.company_mongo_repo.upsert_profile(company)
            self.company_mysql_repo.upsert_company(company)
            trade["gate_status"] = GATE_PROFILE_FETCHED
            fetched_profiles += 1

        self.trade_mysql_repo.upsert_trades(normalized)

        LOGGER.info(
            "Import abgeschlossen: feed=%s raw_inserted=%s clean_upserted=%s profiles=%s",
            len(raw_feed),
            inserted_raw,
            len(normalized),
            fetched_profiles,
        )
        return ImportSummary(
            fetched_feed_records=len(raw_feed),
            inserted_raw_records=inserted_raw,
            upserted_clean_records=len(normalized),
            fetched_profiles=fetched_profiles,
        )

    @staticmethod
    def _normalize_company_profile(profile: dict, fetched_at: datetime) -> dict:
        """Überführt FMP-Profilfelder in das Projektschema."""
        
        # Defensive Typ-Konvertierung für MySQL-Zielsäulen
        mkt_cap = profile.get("mktCap")
        try:
            market_cap = int(float(mkt_cap)) if mkt_cap is not None else None
        except (ValueError, TypeError):
            market_cap = None

        def _to_bool(val: Any) -> bool | None:
            if val is None or val == "":
                return None
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return bool(val)
            if str(val).lower() in ("true", "1", "yes"):
                return True
            if str(val).lower() in ("false", "0", "no"):
                return False
            return None

        return {
            "symbol": str(profile.get("symbol", "")).strip().upper(),
            "company_name": profile.get("companyName"),
            "market_cap": market_cap,
            "price": profile.get("price"),
            "currency": profile.get("currency"),
            "cik": profile.get("cik"),
            "isin": profile.get("isin"),
            "cusip": profile.get("cusip"),
            "exchange": profile.get("exchangeShortName"),
            "exchange_full_name": profile.get("exchange"),
            "industry": profile.get("industry"),
            "sector": profile.get("sector"),
            "country": profile.get("country"),
            "website": profile.get("website"),
            "description": profile.get("description"),
            "ceo": profile.get("ceo"),
            "full_time_employees": str(profile.get("fullTimeEmployees") or "")[:32] or None,
            "ipo_date": profile.get("ipoDate"),
            "is_etf": _to_bool(profile.get("isEtf")),
            "is_actively_trading": _to_bool(profile.get("isActivelyTrading")),
            "is_adr": _to_bool(profile.get("isAdr")),
            "is_fund": _to_bool(profile.get("isFund")),
            "profile_updated_at": fetched_at,
            "profile_payload": profile,
        }
