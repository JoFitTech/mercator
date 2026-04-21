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
from src.db.repositories.company_repository import CompanyMySqlRepository
from src.db.repositories.trade_repository import InsiderTradeMySqlRepository
from src.preprocessing.gate_evaluator import (
    GATE_PASS,
    GATE_PENDING,
    GateEvaluator,
)
from src.services.scoring_service import ScoringService
from src.preprocessing.cleaning import normalize_insider_trade
from src.preprocessing.sector_normalizer import normalize_sector
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
    symbols_considered_for_enrichment: int
    profile_fetch_attempts: int
    profile_cache_hits: int
    profile_failures: int


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
        scoring_service: ScoringService | None = None,
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
        self.scoring_service = scoring_service or ScoringService()

    def run_hourly_import(
        self,
        page: int = DEFAULT_FEED_PAGE,
        limit: int = DEFAULT_FEED_LIMIT,
        profile_fetch_statuses: tuple[str, ...] | None = None,
        force_profile_refresh: bool = False,
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
        elif mode == "ALL_TRADED_COMPANIES" or mode == "ALL TRADED COMPANIES":
            effective_profile_fetch_statuses = {GATE_PASS, GATE_PENDING, "FAIL"} # Eigentlich alle
        elif mode == "DISABLED":
            effective_profile_fetch_statuses = set()
        else:
            # Fallback
            effective_profile_fetch_statuses = {GATE_PASS, GATE_PENDING}

        # 1. Schritt: Alle Trades normalisieren, evaluieren und Stubs erstellen
        unique_company_stubs: dict[str, dict[str, Any]] = {}
        all_traded_symbols: set[str] = set()

        for item in normalized:
            decision = self.gate_evaluator.evaluate(item)
            item["gate_status"] = decision.status
            item["gate_reason"] = decision.reason
            res = self.scoring_service.compute_trade_score(item)
            item["score"] = res["score"]
            item["score_value"] = res["score"]
            item["score_class"] = res["score_class"]
            item["core_insider_score"] = res.get("core_insider_score")
            item["investability_score"] = res.get("investability_score")
            item["execution_score"] = res.get("execution_score")
            item["trade_republic_score"] = res.get("trade_republic_score")
            item["final_score"] = res.get("final_score", res["score"])
            item["final_class"] = res.get("final_class", res["score_class"])
            item["decision_status"] = res.get("decision_status")
            item["filing_age_days"] = res.get("filing_age_days", item.get("filing_age_days"))

            symbol = str(item.get("symbol") or "").strip().upper()
            if symbol:
                all_traded_symbols.add(symbol)

            company_key = item.get("company_key")
            if company_key and company_key not in unique_company_stubs:
                unique_company_stubs[company_key] = item

        # 2. Schritt: Einmaliges Upsert pro Firma
        company_batch: list[dict[str, Any]] = []
        company_lookup_by_key: dict[str, dict[str, Any]] = {}
        for company_key, item in unique_company_stubs.items():
            self._apply_trade_republic_match(item)
            company_stub = self._build_company_stub(item, fetched_at)
            if company_stub:
                company_batch.append(company_stub)
                company_lookup_by_key[company_key] = company_stub

        if company_batch:
            self._persist_company_batch(company_batch)

        inserted_raw = self.raw_repo.upsert_raw_trades(normalized)

        fetched_profiles = 0
        profile_fetch_attempts = 0
        profile_cache_hits = 0
        profile_failures = 0
        
        # Bestimme Symbole für Enrichment
        symbols_to_enrich: set[str] = set()
        
        if mode in ("ALL_TRADED_COMPANIES", "ALL TRADED COMPANIES"):
            symbols_to_enrich = all_traded_symbols
        elif mode != "DISABLED":
            for trade in normalized:
                if trade["gate_status"].upper() in effective_profile_fetch_statuses:
                    sym = str(trade.get("symbol") or "").strip().upper()
                    if sym:
                        symbols_to_enrich.add(sym)
        
        symbols_considered_for_enrichment = len(symbols_to_enrich)
        trades_by_symbol: dict[str, list[dict[str, Any]]] = {}
        for trade in normalized:
            sym = str(trade.get("symbol") or "").strip().upper()
            if sym:
                trades_by_symbol.setdefault(sym, []).append(trade)

        # Führe Enrichment durch
        for symbol in symbols_to_enrich:
            matching_trades = trades_by_symbol.get(symbol, [])
            if not matching_trades:
                continue
            
            sample_trade = matching_trades[0]
            company_key_str = str(sample_trade.get("company_key"))
            
            if not company_key_str:
                continue

            if not force_profile_refresh:
                cached = self.company_mongo_repo.get_recent_profile(
                    company_key=company_key_str,
                    ttl_days=self.fmp_client.config.profile_ttl_days,
                )
                if cached:
                    cached_company = self._prepare_cached_company_profile(
                        cached_profile=cached,
                        symbol=symbol,
                        company_key=company_key_str,
                        fetched_at=fetched_at,
                    )
                    profile_cache_hits += 1
                    self._persist_company_batch([cached_company])
                    company_lookup_by_key[company_key_str] = cached_company
                    for t in matching_trades:
                        t["profile_status"] = cached_company.get("profile_status", "FETCHED")
                        t["profile_reason"] = "cache_hit"
                        if cached_company.get("sector"):
                            t["sector"] = cached_company.get("sector")
                        if cached_company.get("sector_resolution_status"):
                            t["sector_resolution_status"] = cached_company.get("sector_resolution_status")
                        if cached_company.get("market_cap") is not None:
                            t["market_cap"] = cached_company.get("market_cap")
                    continue

            try:
                profile_fetch_attempts += 1
                # Nutze die neue Enrichment-Kette
                company_obj = self.enrichment_service.enrich_company_profile(symbol)
                
                # Konvertiere in Dict für die bestehende Pipeline
                from dataclasses import asdict
                company = asdict(company_obj)
                if not company.get("sector_resolution_status"):
                    company["sector_resolution_status"] = "UNRESOLVED"

                # Metadaten ergänzen
                company["company_key"] = company_key_str
                company["last_seen_at"] = fetched_at
                company["profile_updated_at"] = fetched_at
                company["sync_version"] = 1
                company["profile_status"] = "FETCHED" if company_obj.sector_resolution_status == "RESOLVED" else "FAILED"
                company["profile_reason"] = "api_fetch" if company["profile_status"] == "FETCHED" else "unresolved_sector"
                
                # Backwards compatibility für den Rest des Codes
                profile = company
                
                self._apply_trade_republic_match(company)
                self._persist_company_batch([company])
                company_lookup_by_key[company_key_str] = company
                
                for t in matching_trades:
                    t["profile_status"] = company["profile_status"]
                    t["profile_reason"] = company["profile_reason"]

                if company["profile_status"] == "FETCHED":
                    fetched_profiles += 1
            except Exception:
                LOGGER.exception("Profilabruf fehlgeschlagen für %s", symbol)
                profile_failures += 1
                for t in matching_trades:
                    t["profile_status"] = "FAILED"
                    t["profile_reason"] = "request_failed"
                continue

        # Score und Dashboard-Validität nach Profilanreicherung neu berechnen
        if self.company_mysql_repo is not None and hasattr(self.company_mysql_repo, "get_companies_by_keys"):
            missing_company_keys = [
                str(item.get("company_key"))
                for item in normalized
                if item.get("company_key") and str(item.get("company_key")) not in company_lookup_by_key
            ]
            if missing_company_keys:
                company_lookup_by_key.update(
                    self.company_mysql_repo.get_companies_by_keys(sorted(set(missing_company_keys)))
                )

        for item in normalized:
            self._apply_trade_republic_match(item)
            
            # Sektor-Prüfung für Dashboard-Validität
            # Wenn das Profil geladen wurde, haben wir ggf. jetzt erst einen Sektor.
            company_key = item.get("company_key")
            if company_key:
                comp = company_lookup_by_key.get(str(company_key))
                if comp:
                    item["sector"] = comp.get("sector")
                    item["sector_resolution_status"] = comp.get("sector_resolution_status")
                    item["market_cap"] = comp.get("market_cap")

            res = self.scoring_service.compute_trade_score(item)
            item["score"] = res["score"]
            item["score_value"] = res["score"]
            item["score_class"] = res["score_class"]
            item["core_insider_score"] = res.get("core_insider_score")
            item["investability_score"] = res.get("investability_score")
            item["execution_score"] = res.get("execution_score")
            item["trade_republic_score"] = res.get("trade_republic_score")
            item["final_score"] = res.get("final_score", res["score"])
            item["final_class"] = res.get("final_class", res["score_class"])
            item["decision_status"] = res.get("decision_status")
            item["filing_age_days"] = res.get("filing_age_days", item.get("filing_age_days"))
            
            # Dashboard-Validitätslogik
            item["dashboard_valid"] = self._is_dashboard_valid(item)

        if self.trade_mysql_repo is not None:
            self.trade_mysql_repo.upsert_trades(normalized)
            upserted_clean_records = len(normalized)
        else:
            upserted_clean_records = 0
            LOGGER.warning("Import läuft im Degraded-Mode ohne MySQL-Upsert.")

        LOGGER.info(
            "Import abgeschlossen: feed=%s raw_inserted=%s clean_upserted=%s symbols_considered=%s attempts=%s cache_hits=%s fetched=%s failures=%s force_refresh=%s",
            len(raw_feed),
            inserted_raw,
            upserted_clean_records,
            symbols_considered_for_enrichment,
            profile_fetch_attempts,
            profile_cache_hits,
            fetched_profiles,
            profile_failures,
            force_profile_refresh,
        )
        return ImportSummary(
            fetched_feed_records=len(raw_feed),
            inserted_raw_records=inserted_raw,
            upserted_clean_records=upserted_clean_records,
            fetched_profiles=fetched_profiles,
            symbols_considered_for_enrichment=symbols_considered_for_enrichment,
            profile_fetch_attempts=profile_fetch_attempts,
            profile_cache_hits=profile_cache_hits,
            profile_failures=profile_failures,
        )


    def refresh_company_profile_for_symbol(self, symbol: str) -> dict[str, Any]:
        """Lädt ein einzelnes Unternehmensprofil gezielt nach und persistiert es."""
        normalized_symbol = str(symbol or "").strip().upper()
        if not normalized_symbol:
            return {"ok": False, "message": "Ungültiges Symbol."}

        if self.company_mysql_repo is None:
            return {"ok": False, "message": "MySQL-Repository nicht verfügbar."}

        fetched_at = datetime.now(timezone.utc)
        try:
            existing_company = self.company_mysql_repo.get_company_by_current_symbol(normalized_symbol)
            company_key = (existing_company or {}).get("company_key") or normalized_symbol

            company_obj = self.enrichment_service.enrich_company_profile(normalized_symbol)

            from dataclasses import asdict
            company = asdict(company_obj)
            company.setdefault("sector_resolution_status", "UNRESOLVED")
            company["company_key"] = company_key
            company["current_symbol"] = normalized_symbol
            company["profile_status"] = "FETCHED" if company_obj.sector_resolution_status == "RESOLVED" else "FAILED"
            company["profile_reason"] = "api_fetch" if company["profile_status"] == "FETCHED" else "unresolved_sector"
            company["profile_updated_at"] = fetched_at
            company["last_seen_at"] = fetched_at
            company["source_system"] = "fmp"
            company["sync_version"] = 1

            if existing_company and existing_company.get("first_seen_at"):
                company["first_seen_at"] = existing_company.get("first_seen_at")
            else:
                company["first_seen_at"] = fetched_at
            company["created_at"] = existing_company.get("created_at") if existing_company else fetched_at
            company["updated_at"] = fetched_at

            self._apply_trade_republic_match(company)
            self.company_mongo_repo.upsert_profile(company)
            self.company_mysql_repo.upsert_company(company)

            return {
                "ok": True,
                "message": f"Profil für {normalized_symbol} aktualisiert.",
                "symbol": normalized_symbol,
                "profile_status": company["profile_status"],
            }
        except Exception as exc:
            LOGGER.exception("Gezielter Profil-Refresh fehlgeschlagen für %s", normalized_symbol)
            return {"ok": False, "message": f"Profil-Refresh für {normalized_symbol} fehlgeschlagen: {exc}", "symbol": normalized_symbol}

    @staticmethod
    def _extract_market_cap(profile: dict[str, Any]) -> int | None:
        """Liest Market Cap robust aus unterschiedlichen Provider-Feldnamen."""

        for key in ("market_cap", "marketCap", "mktCap"):
            raw_value = profile.get(key)
            if raw_value in (None, ""):
                continue
            try:
                return int(float(str(raw_value)))
            except (TypeError, ValueError):
                continue
        return None

    def _prepare_cached_company_profile(
        self,
        cached_profile: dict[str, Any],
        symbol: str,
        company_key: str,
        fetched_at: datetime,
    ) -> dict[str, Any]:
        """Normalisiert ein Mongo-Cache-Profil für MySQL-Sync und Re-Use im Import."""

        company = dict(cached_profile)
        company["company_key"] = company_key
        company.setdefault("current_symbol", symbol)
        company.setdefault("source_system", "fmp")
        company.setdefault("sync_version", 1)
        company.setdefault("created_at", fetched_at)
        company["updated_at"] = fetched_at
        company["last_seen_at"] = fetched_at
        company.setdefault("profile_updated_at", fetched_at)

        normalized_sector, method = normalize_sector(
            company.get("sector") or company.get("sector_normalized") or company.get("sector_raw")
        )
        if normalized_sector:
            company["sector"] = normalized_sector
            company.setdefault("sector_raw", company.get("sector") or company.get("sector_normalized") or normalized_sector)
            company["sector_normalized"] = normalized_sector
            company["sector_resolution_status"] = "RESOLVED"
            company.setdefault("sector_resolution_method", f"CACHE_{method}")
            company.setdefault("sector_source", company.get("sector_source") or "CACHE")
            company["profile_status"] = "FETCHED"
            company.setdefault("profile_reason", "cache_hit")
        else:
            company["sector_resolution_status"] = str(company.get("sector_resolution_status") or "UNRESOLVED").upper()
            company.setdefault("profile_status", "FAILED")
            company.setdefault("profile_reason", "cache_hit_unresolved")

        market_cap = self._extract_market_cap(company)
        if market_cap is not None:
            company["market_cap"] = market_cap

        return company

    @staticmethod
    def _normalize_company_profile(profile: dict, trade: dict[str, Any], fetched_at: datetime) -> dict:
        """Überführt FMP-Profilfelder in das Projektschema."""

        # Defensive Typ-Konvertierung für MySQL-Zielsäulen
        mkt_cap = profile.get("mktCap")
        if mkt_cap is None:
            mkt_cap = profile.get("marketCap")
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
            "sector_resolution_status": "UNRESOLVED",
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

    def _build_company_stub(self, trade: dict[str, Any], fetched_at: datetime) -> dict[str, Any] | None:
        company_key = trade.get("company_key")
        if not company_key:
            return None
        return {
            "company_key": company_key,
            "company_cik": trade.get("company_cik"),
            "current_symbol": trade.get("symbol"),
            "company_name": None,
            "sector_resolution_status": "UNRESOLVED",
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

    def _persist_company_batch(self, companies: list[dict[str, Any]]) -> None:
        for company in companies:
            self.company_mongo_repo.upsert_profile(company)
        if self.company_mysql_repo is not None:
            if hasattr(self.company_mysql_repo, "upsert_companies"):
                self.company_mysql_repo.upsert_companies(companies)
            else:
                for company in companies:
                    self.company_mysql_repo.upsert_company(company)

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
            status_map = {"IN_UNIVERSE": "CONFIRMED_MATCH", "NOT_IN_UNIVERSE": "NOT_FOUND", "UNKNOWN": "UNKNOWN"}
            record["tr_availability_state"] = status_map.get(result.status, "UNKNOWN")
            record["tr_tradability_state"] = "OK" if result.status == "IN_UNIVERSE" else "UNKNOWN"
            record["tr_match_confidence"] = result.match_confidence
        except Exception:
            LOGGER.exception("TR matching fehlgeschlagen.")
            record["trade_republic_universe_status"] = "UNKNOWN"
            record["trade_republic_match_method"] = "NONE"
            record["trade_republic_match_confidence"] = "LOW"
            record["tr_availability_state"] = "UNKNOWN"
            record["tr_tradability_state"] = "UNKNOWN"
            record["tr_match_confidence"] = "LOW"

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
