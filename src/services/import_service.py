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
    GATE_PENDING,
    GateEvaluator,
)
from src.preprocessing.cleaning import normalize_insider_trade
from src.services.trade_republic_universe_service import (
    TradeRepublicUniverseIngestionService,
    TradeRepublicUniverseMatchingService,
)

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
        trade_mysql_repo: InsiderTradeMySqlRepository | None,
        company_mysql_repo: CompanyMySqlRepository | None,
        profile_fetch_statuses: tuple[str, ...] = (GATE_PASS, GATE_PENDING),
        allow_write: bool = True,
        tr_ingestion_service: TradeRepublicUniverseIngestionService | None = None,
        tr_matching_service: TradeRepublicUniverseMatchingService | None = None,
    ) -> None:
        self.fmp_client = fmp_client
        self.gate_evaluator = gate_evaluator
        self.raw_repo = raw_repo
        self.company_mongo_repo = company_mongo_repo
        self.trade_mysql_repo = trade_mysql_repo
        self.company_mysql_repo = company_mysql_repo
        self.profile_fetch_statuses = tuple(status.upper() for status in profile_fetch_statuses)
        self.allow_write = allow_write
        self.tr_ingestion_service = tr_ingestion_service
        self.tr_matching_service = tr_matching_service

    def run_hourly_import(
        self,
        page: int = DEFAULT_FEED_PAGE,
        limit: int = DEFAULT_FEED_LIMIT,
        profile_fetch_statuses: tuple[str, ...] | None = None,
    ) -> ImportSummary:
        """Führt einen vollständigen MVP-Importlauf aus."""
        if not self.allow_write:
            raise RuntimeError("Import ist deaktiviert (Review Mode / MERCATOR_DISABLE_IMPORT).")

        fetched_at = datetime.now(timezone.utc)
        try:
            raw_feed = self.fmp_client.fetch_latest_insider_trades(page=page, limit=limit)
        except Exception as exc:
            LOGGER.error("Initialer Feed-Abruf fehlgeschlagen: %s", exc)
            raise RuntimeError(f"Der Datenimport konnte nicht gestartet werden: {exc}") from exc

        normalized = [normalize_insider_trade(item, fetched_at=fetched_at) for item in raw_feed]
        if self.tr_ingestion_service is not None:
            self.tr_ingestion_service.refresh_if_stale(force=False)

        # Fachregel: API-2-Abfrage für Pre-Gate PASS und HOLD.
        effective_profile_fetch_statuses = {GATE_PASS, GATE_PENDING}

        # 1. Schritt: Alle Trades normalisieren, evaluieren und Stubs erstellen
        unique_company_stubs: dict[str, dict[str, Any]] = {}

        for item in normalized:
            decision = self.gate_evaluator.evaluate(item)
            item["gate_status"] = decision.status
            item["gate_reason"] = decision.reason
            score_value, score_class = self._compute_trade_score(item)
            item["score"] = score_value
            item["score_value"] = score_value
            item["score_class"] = score_class

            company_key = item.get("company_key")
            if company_key and company_key not in unique_company_stubs:
                unique_company_stubs[company_key] = item

        # 2. Schritt: Einmaliges Upsert pro Firma
        for company_key, item in unique_company_stubs.items():
            self._apply_trade_republic_match(item)
            self._upsert_company_stub(item, fetched_at)

        inserted_raw = self.raw_repo.upsert_raw_trades(normalized)

        fetched_profiles = 0
        for trade in normalized:
            if trade["gate_status"].upper() not in effective_profile_fetch_statuses:
                continue

            company_key = trade.get("company_key")
            symbol = str(trade.get("symbol") or "").strip().upper() or None
            company_cik_raw = trade.get("company_cik")
            if not company_key:
                trade["profile_status"] = "FAILED"
                trade["profile_reason"] = "company_key fehlt"
                continue
            company_key_str = str(company_key)
            company_cik_value: str = self._to_text(company_cik_raw).strip()

            cached = self.company_mongo_repo.get_recent_profile(
                company_key=company_key_str,
                ttl_days=self.fmp_client.config.profile_ttl_days,
            )
            if cached:
                trade["profile_status"] = "FETCHED"
                trade["profile_reason"] = "cache_hit"
                continue

            try:
                profile = None
                lookup_mode: str = self._to_text(self.fmp_client.config.lookup_mode)
                if lookup_mode == "cik_primary_symbol_fallback" and len(company_cik_value) > 0:
                    profile = self.fmp_client.fetch_company_profile_by_cik(company_cik_value)
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
            self._apply_trade_republic_match(company)
            self.company_mongo_repo.upsert_profile(company)
            if self.company_mysql_repo is not None:
                self.company_mysql_repo.upsert_company(company)
            trade["profile_status"] = "FETCHED"
            trade["profile_reason"] = "api_fetch"
            fetched_profiles += 1

        # Score nach Profilanreicherung neu berechnen (MarketCap/Validity kann sich ändern)
        for item in normalized:
            self._apply_trade_republic_match(item)
            score_value, score_class = self._compute_trade_score(item)
            item["score"] = score_value
            item["score_value"] = score_value
            item["score_class"] = score_class

        if self.trade_mysql_repo is not None:
            self.trade_mysql_repo.upsert_trades(normalized)
            upserted_clean_records = len(normalized)
        else:
            upserted_clean_records = 0
            LOGGER.warning("Import läuft im Degraded-Mode ohne MySQL-Upsert.")

        LOGGER.info(
            "Import abgeschlossen: feed=%s raw_inserted=%s clean_upserted=%s profiles=%s",
            len(raw_feed),
            inserted_raw,
            upserted_clean_records,
            fetched_profiles,
        )
        return ImportSummary(
            fetched_feed_records=len(raw_feed),
            inserted_raw_records=inserted_raw,
            upserted_clean_records=upserted_clean_records,
            fetched_profiles=fetched_profiles,
        )

    @staticmethod
    def _normalize_company_profile(profile: dict, trade: dict[str, Any], fetched_at: datetime) -> dict:
        """Überführt FMP-Profilfelder in das Projektschema."""

        # Defensive Typ-Konvertierung für MySQL-Zielsäulen
        mkt_cap = profile.get("mktCap")
        try:
            market_cap = int(float(str(mkt_cap))) if mkt_cap is not None else None
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
            "source_system": "fmp",
            "sync_version": 1,
            "created_at": trade.get("first_seen_at") or fetched_at,
            "updated_at": fetched_at,
            "profile_payload": profile,
        }

    @staticmethod
    def _to_text(value: Any) -> str:
        """Konvertiert optionale/heterogene Werte defensiv in String."""

        return "" if value is None else str(value)

    @staticmethod
    def _compute_trade_score(trade: dict[str, Any]) -> tuple[float | None, str | None]:
        """Berechnet Score und Klasse für Persistenzfelder score/score_class."""
        try:
            trade_value = float(trade.get("trade_value_estimated") or 0)
            acquisition = str(trade.get("acquisition_or_disposition") or "").upper()
            validation_status = str(trade.get("validation_status") or "VALID").upper()
            profile_status = str(trade.get("profile_status") or "NOT_REQUESTED").upper()
            owner = str(trade.get("type_of_owner") or "").lower()
            market_cap = float(trade.get("market_cap") or 0)

            value_score = min(1.0, max(0.0, (trade_value - 100_000) / (10_000_000 - 100_000)))
            direction_score = 1.0 if acquisition == "A" else (0.5 if acquisition == "D" else 0.0)
            mcap_score = min(1.0, max(0.0, (market_cap - 100_000_000) / (500_000_000_000 - 100_000_000)))
            validity_score = (0.5 if validation_status == "VALID" else 0.0) + (0.5 if profile_status == "FETCHED" else 0.0)
            role_score = 1.0 if any(token in owner for token in ("officer", "director", "ceo", "cfo")) else 0.5

            score = round((value_score * 0.35 + direction_score * 0.20 + mcap_score * 0.15 + validity_score * 0.15 + role_score * 0.15) * 100, 2)
            score_class = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D" if score >= 20 else "E"
            return score, score_class
        except (TypeError, ValueError):
            return None, None

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
            "source_system": "fmp",
            "sync_version": 1,
            "created_at": trade.get("first_seen_at") or fetched_at,
            "updated_at": fetched_at,
        }
        self.company_mongo_repo.upsert_profile(company_stub)
        if self.company_mysql_repo is not None:
            self.company_mysql_repo.upsert_company(company_stub)

    def _apply_trade_republic_match(self, record: dict[str, Any]) -> None:
        if self.tr_matching_service is None:
            record.setdefault("trade_republic_universe_status", "UNKNOWN")
            record.setdefault("trade_republic_match_method", "NONE")
            record.setdefault("trade_republic_match_confidence", "LOW")
            return
        try:
            result = self.tr_matching_service.match_company(
                company_isin=record.get("isin"),
                symbol=record.get("current_symbol") or record.get("symbol") or record.get("symbol_at_trade"),
                company_name=record.get("company_name") or record.get("raw_payload", {}).get("companyName"),
            )
            record["trade_republic_universe_status"] = result.status
            record["trade_republic_match_method"] = result.match_method
            record["trade_republic_match_confidence"] = result.match_confidence
            record["trade_republic_source_refreshed_at"] = result.source_refreshed_at
            record["trade_republic_reference_isin"] = result.reference_isin
            record["trade_republic_reference_name"] = result.reference_name
        except Exception:
            LOGGER.exception("TR matching fehlgeschlagen.")
            record["trade_republic_universe_status"] = "UNKNOWN"
            record["trade_republic_match_method"] = "NONE"
            record["trade_republic_match_confidence"] = "LOW"
