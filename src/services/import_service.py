"""Import-Service für FMP-Feed, Verarbeitung und Persistenz."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.config.settings import DEFAULT_FEED_LIMIT, DEFAULT_FEED_PAGE
from src.data_sources.fmp_client import FmpClient
from src.data_sources.alpha_vantage_client import AlphaVantageClient
from src.data_sources.polygon_client import PolygonClient
from src.services.company_enrichment_service import CompanyEnrichmentService
from src.db.mongo_repository import CompanyMongoRepository, InsiderTradeMongoRepository
from src.db.mysql_repository import CompanyMySqlRepository, InsiderTradeMySqlRepository
from src.preprocessing.gate_evaluator import (
    GATE_PASS,
    GATE_PENDING,
    GateEvaluator,
)
from src.domain_rules import compute_discrete_score
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
        api2_firing_mode: str = "PASS + PENDING",
        allow_write: bool = True,
        tr_ingestion_service: TradeRepublicUniverseIngestionService | None = None,
        tr_matching_service: TradeRepublicUniverseMatchingService | None = None,
        enrichment_service: CompanyEnrichmentService | None = None,
    ) -> None:
        self.fmp_client = fmp_client
        self.gate_evaluator = gate_evaluator
        self.raw_repo = raw_repo
        self.company_mongo_repo = company_mongo_repo
        self.trade_mysql_repo = trade_mysql_repo
        self.company_mysql_repo = company_mysql_repo
        self.profile_fetch_statuses = tuple(status.upper() for status in profile_fetch_statuses)
        self.api2_firing_mode = api2_firing_mode
        self.allow_write = allow_write
        self.tr_ingestion_service = tr_ingestion_service
        self.tr_matching_service = tr_matching_service
        self.enrichment_service = enrichment_service or CompanyEnrichmentService(fmp_client)

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

        # Fachregel: API-2-Abfrage steuerbar (Requirement 2.3)
        mode = str(self.api2_firing_mode).upper()
        if mode == "ONLY PASS":
            effective_profile_fetch_statuses = {GATE_PASS}
        elif mode == "PASS + PENDING":
            effective_profile_fetch_statuses = {GATE_PASS, GATE_PENDING}
        elif mode == "ALL VALID":
            # Alle validen Trades (PASS, PENDING, FAIL - solange validation_status VALID ist)
            effective_profile_fetch_statuses = {GATE_PASS, GATE_PENDING, "FAIL"}
        elif mode == "DISABLED":
            effective_profile_fetch_statuses = set()
        else:
            # Fallback
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
                # Nutze die neue Enrichment-Kette
                company_obj = self.enrichment_service.enrich_company_profile(symbol)
                
                # Konvertiere in Dict für die bestehende Pipeline
                from dataclasses import asdict
                company = asdict(company_obj)
                
                # Metadaten ergänzen
                company["company_key"] = company_key_str
                company["last_seen_at"] = fetched_at
                company["profile_updated_at"] = fetched_at
                company["sync_version"] = 1
                company["profile_status"] = "FETCHED" if company_obj.sector_resolution_status == "RESOLVED" else "FAILED"
                company["profile_reason"] = "api_fetch" if company["profile_status"] == "FETCHED" else "unresolved_sector"
                
                # Backwards compatibility für den Rest des Codes
                profile = company
            except Exception:
                LOGGER.exception("Profilabruf fehlgeschlagen für %s", symbol)
                trade["profile_status"] = "FAILED"
                trade["profile_reason"] = "request_failed"
                continue

            # if not profile: - nicht mehr nötig, da enrichment_service immer ein Objekt liefert
            
            # self._normalize_company_profile wird nicht mehr benötigt, da enrichment_service das erledigt
            # company = self._normalize_company_profile(profile, trade=trade, fetched_at=fetched_at)
            
            self._apply_trade_republic_match(company)
            self.company_mongo_repo.upsert_profile(company)
            if self.company_mysql_repo is not None:
                self.company_mysql_repo.upsert_company(company)
            trade["profile_status"] = "FETCHED"
            trade["profile_reason"] = "api_fetch"
            fetched_profiles += 1

        # Score und Dashboard-Validität nach Profilanreicherung neu berechnen
        for item in normalized:
            self._apply_trade_republic_match(item)
            
            # Sektor-Prüfung für Dashboard-Validität
            # Wenn das Profil geladen wurde, haben wir ggf. jetzt erst einen Sektor.
            company_key = item.get("company_key")
            if company_key and self.company_mysql_repo:
                # Da wir gerade ge-upserted haben, können wir den Sektor-Status kurz prüfen
                comp = self.company_mysql_repo.get_company_by_symbol(company_key)
                if comp:
                    item["sector"] = comp.get("sector")
                    item["sector_resolution_status"] = comp.get("sector_resolution_status")
                    item["market_cap"] = comp.get("market_cap")

            score_value, score_class = self._compute_trade_score(item)
            item["score"] = score_value
            item["score_value"] = score_value
            item["score_class"] = score_class
            
            # Dashboard-Validitätslogik
            item["dashboard_valid"] = self._is_dashboard_valid(item)

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
        """Berechnet Score und Klasse basierend auf der diskreten Domain-Logik."""
        return compute_discrete_score(trade)

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

    def _is_dashboard_valid(self, trade: dict[str, Any]) -> bool:
        """Prüft, ob ein Trade alle Kriterien für das Dashboard erfüllt."""
        # 1. Symbol vorhanden
        if not trade.get("symbol") and not trade.get("symbol_at_trade"):
            return False
            
        # 2. Price gültig
        price = trade.get("price")
        if price is None or price <= 0:
            return False
            
        # 3. Qty gültig
        qty = trade.get("qty")
        if qty is None or qty <= 0:
            return False
            
        # 4. Direction gültig
        direction = trade.get("acquisition_or_disposition")
        if not direction or direction.upper() not in ("A", "D", "BUY", "SELL"):
            return False
            
        # 5. Sektor belastbar aufgelöst
        # Wir prüfen sowohl den aktuellen Datensatz als auch den Status
        sector = trade.get("sector")
        res_status = trade.get("sector_resolution_status")
        
        if not sector or str(sector).lower() in ("unknown", "n/a", "none", ""):
            return False
            
        if res_status and res_status.upper() == "UNRESOLVED":
            return False
            
        return True
