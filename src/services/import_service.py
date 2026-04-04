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
            self._upsert_company_stub(item, fetched_at)

        inserted_raw = self.raw_repo.upsert_raw_trades(normalized)

        fetched_profiles = 0
        for trade in normalized:
            if trade["gate_status"].upper() not in effective_profile_fetch_statuses:
                continue

            company_key = trade.get("company_key")
            symbol = trade.get("symbol")
            company_cik = trade.get("company_cik")
            if not company_key:
                trade["profile_status"] = "FAILED"
                trade["profile_reason"] = "company_key fehlt"
                continue

            cached = self.company_mongo_repo.get_recent_profile(
                company_key=company_key,
                ttl_days=self.fmp_client.config.profile_ttl_days,
            )
            if cached:
                trade["profile_status"] = "FETCHED"
                trade["profile_reason"] = "cache_hit"
                continue

            try:
                profile = None
                if company_cik and self.fmp_client.config.lookup_mode == "cik_primary_symbol_fallback":
                    profile = self.fmp_client.fetch_company_profile_by_cik(str(company_cik))
                if not profile and symbol:
                    profile = self.fmp_client.fetch_company_profile(symbol)
            except Exception:
                LOGGER.exception("Profilabruf fehlgeschlagen für %s", symbol)
                trade["profile_status"] = "FAILED"
                trade["profile_reason"] = "request_failed"
                continue

            if not profile:
                trade["profile_status"] = "FAILED"
                trade["profile_reason"] = "empty_response"
                continue

            company = self._normalize_company_profile(profile, trade=trade, fetched_at=fetched_at)
            self.company_mongo_repo.upsert_profile(company)
            self.company_mysql_repo.upsert_company(company)
            trade["profile_status"] = "FETCHED"
            trade["profile_reason"] = "api_fetch"
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
    def _normalize_company_profile(profile: dict, trade: dict[str, Any], fetched_at: datetime) -> dict:
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
            "company_key": trade.get("company_key"),
            "company_cik": profile.get("cik") or trade.get("company_cik"),
            "current_symbol": str(profile.get("symbol") or trade.get("symbol") or "").strip().upper() or None,
            "company_name": profile.get("companyName") or trade.get("raw_payload", {}).get("companyName"),
            "profile_status": "FETCHED",
            "profile_reason": None,
            "first_seen_at": trade.get("first_seen_at"),
            "last_seen_at": fetched_at,
            "market_cap": market_cap,
            "price": profile.get("price"),
            "currency": profile.get("currency"),
            "isin": profile.get("isin"),
            "cusip": profile.get("cusip"),
            "exchange": profile.get("exchangeShortName") or profile.get("exchange"),
            "exchange_full_name": profile.get("exchangeFullName") or profile.get("exchange"),
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

    def _upsert_company_stub(self, trade: dict[str, Any], fetched_at: datetime) -> None:
        company_key = trade.get("company_key")
        if not company_key:
            return
        company_stub = {
            "company_key": company_key,
            "company_cik": trade.get("company_cik"),
            "current_symbol": trade.get("symbol"),
            "company_name": None,
            "profile_status": "NOT_REQUESTED",
            "profile_reason": None,
            "first_seen_at": trade.get("first_seen_at") or fetched_at,
            "last_seen_at": fetched_at,
            "profile_updated_at": None,
        }
        self.company_mongo_repo.upsert_profile(company_stub)
        self.company_mysql_repo.upsert_company(company_stub)
