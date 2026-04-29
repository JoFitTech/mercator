"""Import-Service für FMP-Feed, Verarbeitung und Persistenz."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.config.settings import DEFAULT_FEED_LIMIT, DEFAULT_FEED_PAGE
from src.data_sources.fmp_client import FmpClient
from src.services.company_enrichment_service import CompanyEnrichmentService
from src.services.company_profile_enrichment_service import CompanyProfileEnrichmentService
from src.services.historical_market_data_service import HistoricalMarketDataService
from src.db.repositories.market_signal_cache_repository import MarketSignalCacheRepository
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
from src.preprocessing.normalization import parse_datetime, parse_float
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
    skipped_raw_duplicates: int = 0
    raw_storage_error: str | None = None


@dataclass(slots=True)
class ProfileBackfillSummary:
    candidates: int
    attempted: int
    refreshed: int
    failed: int


@dataclass(slots=True)
class RawCleanSyncSummary:
    raw_candidates: int
    clean_upserted: int
    skipped_missing_dedupe: int
    skipped_validation_failed: int = 0
    skipped_processing_error: int = 0


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
        api2_firing_mode: str = "ONLY PASS",
        allow_write: bool = True,
        tr_ingestion_service: TradeRepublicUniverseIngestionService | None = None,
        tr_matching_service: TradeRepublicUniverseMatchingService | None = None,
        enrichment_service: CompanyEnrichmentService | None = None,
        scoring_service: ScoringService | None = None,
        historical_service: HistoricalMarketDataService | None = None,
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
        self.profile_service = CompanyProfileEnrichmentService(fmp_client)
        if historical_service is not None:
            self.historical_service = historical_service
        elif trade_mysql_repo is not None and hasattr(trade_mysql_repo, "_client"):
            cache_repo = MarketSignalCacheRepository(trade_mysql_repo._client)  # type: ignore[attr-defined]
            self.historical_service = HistoricalMarketDataService(fmp_client, cache_repo=cache_repo)
        else:
            self.historical_service = HistoricalMarketDataService(fmp_client)
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
        import_run_id = fetched_at.strftime("import_%Y%m%dT%H%M%S%fZ")
        try:
            raw_feed = self.fmp_client.fetch_latest_insider_trades(page=page, limit=limit)
        except Exception as exc:
            LOGGER.error("Initialer Feed-Abruf fehlgeschlagen: %s", exc)
            raise RuntimeError(f"Der Datenimport konnte nicht gestartet werden: {exc}") from exc

        normalized = [normalize_insider_trade(item, fetched_at=fetched_at) for item in raw_feed]

        # Raw-Audit-Metadaten unmittelbar nach API1-Fetch anreichern.
        for item in normalized:
            dedupe_key = str(item.get("dedupe_key") or "").strip()
            item["source"] = "fmp"
            item["source_endpoint"] = "/stable/insider-trading/latest"
            item["import_run_id"] = import_run_id
            item["imported_at"] = fetched_at
            item["source_hash"] = dedupe_key or None
            item["trade_hash"] = dedupe_key or None
            item["normalized_symbol"] = item.get("symbol")
            item["processing_status"] = "RAW_IMPORTED"

        raw_storage_error: str | None = None
        try:
            inserted_raw = self.raw_repo.upsert_raw_trades(normalized)
        except Exception as exc:
            # Import darf weiterlaufen (Clean-Pfad), aber Raw-Fehler wird klar ausgewiesen.
            raw_storage_error = f"Mongo raw storage failed: {exc}"
            LOGGER.warning(raw_storage_error)
            inserted_raw = 0

        skipped_raw_duplicates = max(0, len(normalized) - int(inserted_raw))

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
            # Fallback: nur Gate-PASS (spec-konform)
            effective_profile_fetch_statuses = {GATE_PASS}

        # 1. Schritt: Alle Trades normalisieren, evaluieren und Stubs erstellen
        unique_company_stubs: dict[str, dict[str, Any]] = {}
        all_traded_symbols: set[str] = set()

        for item in normalized:
            decision = self.gate_evaluator.evaluate(item)
            item["gate_status"] = decision.status
            item["gate_reason"] = decision.reason

            symbol = str(item.get("symbol") or "").strip().upper()
            if symbol:
                all_traded_symbols.add(symbol)

            company_key_str: str = str(item.get("company_key") or "").strip()
            if company_key_str and company_key_str not in unique_company_stubs:
                unique_company_stubs[company_key_str] = item

        # 2. Schritt: Einmaliges Upsert pro Firma (Stub zuerst persistieren)
        company_batch_by_key: dict[str, dict[str, Any]] = {}
        company_lookup_by_key: dict[str, dict[str, Any]] = {}
        initial_stubs: list[dict[str, Any]] = []
        for company_key, item in unique_company_stubs.items():
            self._apply_trade_republic_match(item)
            company_stub = self._build_company_stub(item, fetched_at)
            if company_stub:
                company_batch_by_key[str(company_key)] = company_stub
                company_lookup_by_key[company_key] = company_stub
                initial_stubs.append(company_stub)
        if initial_stubs:
            self._persist_company_batch(initial_stubs)

        fetched_profiles = 0
        profile_fetch_attempts = 0
        profile_cache_hits = 0
        profile_failures = 0
        
        # Bestimme Symbole für API2-Profilanreicherung
        symbols_to_enrich: set[str] = set()

        api2_skip_by_gate = 0
        for trade in normalized:
            symbol = str(trade.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            gate_status = str(trade.get("gate_status") or "").upper()
            if mode in ("ALL_TRADED_COMPANIES", "ALL TRADED COMPANIES"):
                symbols_to_enrich.add(symbol)
                continue
            if gate_status not in effective_profile_fetch_statuses:
                api2_skip_by_gate += 1
                continue
            symbols_to_enrich.add(symbol)

        symbols_considered_for_enrichment = len(symbols_to_enrich)
        trades_by_symbol: dict[str, list[dict[str, Any]]] = {}
        for trade in normalized:
            sym = str(trade.get("symbol") or "").strip().upper()
            if sym:
                trades_by_symbol.setdefault(sym, []).append(trade)

        symbols_with_profile_success: set[str] = set()

        # Führe Enrichment durch
        # OPTIMIERUNG: Batch-Cache-Lookup statt N einzelner get_recent_profile-Aufrufe
        profile_company_batch: list[dict[str, Any]] = []
        
        # Sammle die company_keys für Bulk-Cache-Suche
        company_keys_for_cache_lookup: set[str] = set()
        for symbol in symbols_to_enrich:
            matching_trades = trades_by_symbol.get(symbol, [])
            if not matching_trades:
                continue
            sample_trade = matching_trades[0]
            company_key_str = str(sample_trade.get("company_key") or "").strip()
            if company_key_str:
                company_keys_for_cache_lookup.add(company_key_str)
        
        # Hole alle Cache-Profile auf einmal (statt N Einzelabfragen)
        cached_profiles_bulk: dict[str, dict[str, Any]] = {}
        if company_keys_for_cache_lookup and not force_profile_refresh:
            if hasattr(self.company_mongo_repo, "get_recent_profiles_bulk"):
                try:
                    cached_profiles_bulk = self.company_mongo_repo.get_recent_profiles_bulk(
                        sorted(company_keys_for_cache_lookup),
                        ttl_days=self.fmp_client.config.profile_ttl_days,
                    )
                except Exception:
                    LOGGER.exception("Bulk-Cache-Abfrage fehlgeschlagen; fahre ohne Cache-Hits fort")
                    cached_profiles_bulk = {}
            else:
                # Fallback: einzelne Cache-Abfragen
                ttl_days = self.fmp_client.config.profile_ttl_days
                for _ck in company_keys_for_cache_lookup:
                    try:
                        _cached = self.company_mongo_repo.get_recent_profile(_ck, ttl_days)
                        if _cached:
                            cached_profiles_bulk[_ck] = _cached
                    except Exception:
                        pass

        # Verarbeite die Symbole mit den gecachten Profilen
        for symbol in symbols_to_enrich:
            matching_trades = trades_by_symbol.get(symbol, [])
            if not matching_trades:
                continue
            
            sample_trade = matching_trades[0]
            company_key_str = str(sample_trade.get("company_key") or "").strip()
            
            if not company_key_str:
                continue

            if not force_profile_refresh:
                # Versuche zuerst Bulk-Cache
                cached = cached_profiles_bulk.get(company_key_str)

                if cached:
                    cached_company = self._prepare_cached_company_profile(
                        cached_profile=cached,
                        symbol=symbol,
                        company_key=company_key_str,
                        fetched_at=fetched_at,
                    )
                    profile_cache_hits += 1
                    profile_company_batch.append(cached_company)
                    company_batch_by_key[company_key_str] = cached_company
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
                if hasattr(self.fmp_client, "fetch_company_profile"):
                    profile_payload = self.profile_service.fetch_profile(symbol)
                    mapped = self.profile_service.map_profile_fields(profile_payload)
                    company = {
                        "company_key": company_key_str,
                        "current_symbol": symbol,
                        "company_name": mapped.get("company_name"),
                        "market_cap": mapped.get("market_cap"),
                        "price": mapped.get("profile_price"),
                        "industry": mapped.get("industry"),
                        "company_cik": mapped.get("cik"),
                        "isin": mapped.get("isin"),
                        "cusip": mapped.get("cusip"),
                        "exchange": mapped.get("exchange"),
                        "country": mapped.get("country"),
                        "sector": mapped.get("sector"),
                        "website": mapped.get("website"),
                        "description": mapped.get("description"),
                        "ceo": mapped.get("ceo"),
                        "full_time_employees": mapped.get("full_time_employees"),
                        "profile_updated_at": fetched_at,
                        "last_seen_at": fetched_at,
                        "sync_version": 1,
                        "profile_status": "FETCHED" if mapped else "FAILED",
                        "profile_reason": "api2_v2",
                        "source": "fmp",
                        "source_endpoint": "/stable/profile",
                        "import_run_id": import_run_id,
                        "imported_at": fetched_at,
                        "raw_payload": profile_payload,
                    }
                else:
                    company_obj = self.enrichment_service.enrich_company_profile(symbol)
                    from dataclasses import asdict
                    company = asdict(company_obj)
                    company["company_key"] = company_key_str
                    company["last_seen_at"] = fetched_at
                    company["profile_updated_at"] = fetched_at
                    company["sync_version"] = 1
                    company["profile_status"] = "FETCHED" if company_obj.sector_resolution_status == "RESOLVED" else "FAILED"
                    company["profile_reason"] = "api_fetch" if company["profile_status"] == "FETCHED" else "unresolved_sector"
                    company["source"] = "fmp"
                    company["source_endpoint"] = "/stable/profile"
                    company["import_run_id"] = import_run_id
                    company["imported_at"] = fetched_at

                self._apply_trade_republic_match(company)
                profile_company_batch.append(company)
                company_batch_by_key[company_key_str] = company
                company_lookup_by_key[company_key_str] = company
                
                for t in matching_trades:
                    t["profile_status"] = company["profile_status"]
                    t["profile_reason"] = company["profile_reason"]

                if company["profile_status"] == "FETCHED":
                    fetched_profiles += 1
                    symbols_with_profile_success.add(symbol)
            except Exception:
                LOGGER.exception("Profilabruf fehlgeschlagen für %s", symbol)
                profile_failures += 1
                for t in matching_trades:
                    t["profile_status"] = "FAILED"
                    t["profile_reason"] = "request_failed"
                    t["processing_status"] = "API2_FAILED"
                continue
        if profile_company_batch:
            self._persist_company_batch(profile_company_batch)

        if not symbols_to_enrich:
            LOGGER.info(
                "API2 uebersprungen: mode=%s effective_statuses=%s (keine Symbole qualifiziert).",
                mode,
                sorted(effective_profile_fetch_statuses),
            )
        elif api2_skip_by_gate:
            LOGGER.info(
                "API2 gate filter: mode=%s effective_statuses=%s skipped_trades=%s selected_symbols=%s",
                mode,
                sorted(effective_profile_fetch_statuses),
                api2_skip_by_gate,
                len(symbols_to_enrich),
            )

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

        # API3 nur für Gate-Passer mit erfolgreichem API2-Profil
        api3_skipped_no_gate_pass = 0
        api3_skipped_no_api2_profile = 0
        api3_skipped_missing_client_method = 0
        attempted_api3_symbols = 0
        for symbol in symbols_with_profile_success:
            matching_trades = trades_by_symbol.get(symbol, [])
            if not matching_trades:
                continue
            if not any(str(t.get("gate_status", "")).upper() == GATE_PASS for t in matching_trades):
                api3_skipped_no_gate_pass += 1
                continue
            try:
                if not hasattr(self.fmp_client, "fetch_historical_price_eod_full"):
                    api3_skipped_missing_client_method += 1
                    continue
                attempted_api3_symbols += 1
                signal = self.historical_service.load_signal(symbol)
                for t in matching_trades:
                    t["avg_20d_volume"] = signal.avg_20d_volume
                    t["avg_20d_dollar_volume"] = signal.avg_20d_dollar_volume
                    t["sma_50"] = signal.sma_50
                    t["sma_200"] = signal.sma_200
                    t["momentum_3m"] = signal.momentum_3m
                    t["momentum_6m"] = signal.momentum_6m
                    t["technical_state"] = signal.technical_state
                    t["liquidity_state"] = signal.liquidity_state
            except Exception:
                LOGGER.exception("API3 historical enrichment fehlgeschlagen für %s", symbol)

        api3_candidate_symbols = {
            symbol
            for symbol, symbol_trades in trades_by_symbol.items()
            if any(str(t.get("gate_status", "")).upper() == GATE_PASS for t in symbol_trades)
        }
        api3_skipped_no_api2_profile = len(api3_candidate_symbols - symbols_with_profile_success)
        if api3_candidate_symbols:
            LOGGER.info(
                "API3 status: candidates=%s attempted=%s skipped_no_api2_profile=%s skipped_no_gate_pass=%s skipped_missing_method=%s",
                len(api3_candidate_symbols),
                attempted_api3_symbols,
                api3_skipped_no_api2_profile,
                api3_skipped_no_gate_pass,
                api3_skipped_missing_client_method,
            )
        else:
            LOGGER.info("API3 uebersprungen: keine Gate-PASS Kandidaten vorhanden.")

        self._score_and_mark_clean_candidates(normalized, company_lookup_by_key)
        clean_upsert_batch = self._build_clean_upsert_batch(normalized)

        if self.trade_mysql_repo is not None:
            self.trade_mysql_repo.upsert_trades(clean_upsert_batch)
            upserted_clean_records = len(clean_upsert_batch)
            self._update_company_trade_stats(clean_upsert_batch)
            if hasattr(self.trade_mysql_repo, "bump_dashboard_state"):
                self.trade_mysql_repo.bump_dashboard_state()
        else:
            upserted_clean_records = 0
            LOGGER.warning("Import läuft im Degraded-Mode ohne MySQL-Upsert.")

        LOGGER.info(
            "Import abgeschlossen: feed=%s raw_inserted=%s raw_duplicates=%s clean_upserted=%s symbols_considered=%s attempts=%s cache_hits=%s fetched=%s failures=%s force_refresh=%s",
            len(raw_feed),
            inserted_raw,
            skipped_raw_duplicates,
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
            skipped_raw_duplicates=skipped_raw_duplicates,
            raw_storage_error=raw_storage_error,
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

    def backfill_missing_profiles(self, max_symbols: int = 50, force_refresh: bool = True) -> ProfileBackfillSummary:
        """Lädt gezielt fehlende/unvollständige Firmenprofile per API2 nach."""
        if self.company_mysql_repo is None:
            return ProfileBackfillSummary(candidates=0, attempted=0, refreshed=0, failed=0)
        if not hasattr(self.company_mysql_repo, "list_profile_backfill_candidates"):
            return ProfileBackfillSummary(candidates=0, attempted=0, refreshed=0, failed=0)

        candidates = self.company_mysql_repo.list_profile_backfill_candidates(limit=max_symbols)
        attempted = 0
        refreshed = 0
        failed = 0

        for symbol in candidates:
            attempted += 1
            result = self.refresh_company_profile_for_symbol(symbol)
            if bool(result.get("ok")):
                refreshed += 1
            else:
                failed += 1

        LOGGER.info(
            "API2 backfill abgeschlossen: candidates=%s attempted=%s refreshed=%s failed=%s force_refresh=%s",
            len(candidates),
            attempted,
            refreshed,
            failed,
            force_refresh,
        )
        return ProfileBackfillSummary(
            candidates=len(candidates),
            attempted=attempted,
            refreshed=refreshed,
            failed=failed,
        )

    def sync_raw_to_clean(self, limit: int = 200) -> RawCleanSyncSummary:
        """Synchronisiert vorhandene Raw-Trades aus MongoDB nach MySQL (ohne neue API-Aufrufe)."""
        if not self.allow_write:
            raise RuntimeError("Raw->Clean-Sync ist deaktiviert (Review Mode / MERCATOR_DISABLE_IMPORT).")
        if self.trade_mysql_repo is None:
            raise RuntimeError("Raw->Clean-Sync nicht möglich: MySQL-Repository fehlt.")
        if not hasattr(self.raw_repo, "list_latest_raw_trades"):
            raise RuntimeError("Raw->Clean-Sync nicht möglich: Raw-Repository unterstützt keinen Listenabruf.")

        raw_rows = self.raw_repo.list_latest_raw_trades(limit=int(limit))
        if not raw_rows:
            return RawCleanSyncSummary(raw_candidates=0, clean_upserted=0, skipped_missing_dedupe=0)

        fetched_at = datetime.now(timezone.utc)
        sync_candidates: list[dict[str, Any]] = []
        skipped_missing_dedupe = 0
        skipped_processing_error = 0
        for row in raw_rows:
            try:
                prepared = self._prepare_raw_trade_for_sync(row, fetched_at=fetched_at)
            except Exception:
                LOGGER.exception("Raw->Clean-Sync: Datensatz konnte nicht vorbereitet werden und wird uebersprungen.")
                skipped_processing_error += 1
                continue
            dedupe_key = str(prepared.get("dedupe_key") or "").strip()
            if not dedupe_key:
                skipped_missing_dedupe += 1
                continue
            sync_candidates.append(prepared)

        if not sync_candidates:
            return RawCleanSyncSummary(
                raw_candidates=len(raw_rows),
                clean_upserted=0,
                skipped_missing_dedupe=skipped_missing_dedupe,
                skipped_processing_error=skipped_processing_error,
            )

        self._evaluate_gates(sync_candidates)
        company_lookup_by_key = self._apply_existing_company_context(sync_candidates)
        self._score_and_mark_clean_candidates(sync_candidates, company_lookup_by_key)
        clean_upsert_batch = self._build_clean_upsert_batch(sync_candidates)
        skipped_validation_failed = max(0, len(sync_candidates) - len(clean_upsert_batch))

        if clean_upsert_batch:
            self.trade_mysql_repo.upsert_trades(clean_upsert_batch)
            self._update_company_trade_stats(clean_upsert_batch)
            if hasattr(self.trade_mysql_repo, "bump_dashboard_state"):
                self.trade_mysql_repo.bump_dashboard_state()

        upserted = len(clean_upsert_batch)

        LOGGER.info(
            "Raw->Clean-Sync abgeschlossen: raw_candidates=%s clean_upserted=%s skipped_missing_dedupe=%s skipped_validation_failed=%s skipped_processing_error=%s",
            len(raw_rows),
            upserted,
            skipped_missing_dedupe,
            skipped_validation_failed,
            skipped_processing_error,
        )
        return RawCleanSyncSummary(
            raw_candidates=len(raw_rows),
            clean_upserted=upserted,
            skipped_missing_dedupe=skipped_missing_dedupe,
            skipped_validation_failed=skipped_validation_failed,
            skipped_processing_error=skipped_processing_error,
        )

    def _evaluate_gates(self, trades: list[dict[str, Any]]) -> None:
        for item in trades:
            decision = self.gate_evaluator.evaluate(item)
            item["gate_status"] = decision.status
            item["gate_reason"] = decision.reason

    def _apply_existing_company_context(
        self,
        trades: list[dict[str, Any]],
        company_lookup_by_key: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, dict[str, Any]]:
        lookup: dict[str, dict[str, Any]] = dict(company_lookup_by_key or {})
        if self.company_mysql_repo is not None and hasattr(self.company_mysql_repo, "get_companies_by_keys"):
            missing_keys = [
                str(item.get("company_key"))
                for item in trades
                if item.get("company_key") and str(item.get("company_key")) not in lookup
            ]
            if missing_keys:
                lookup.update(self.company_mysql_repo.get_companies_by_keys(sorted(set(missing_keys))))

        for item in trades:
            company_key = item.get("company_key")
            if not company_key:
                continue
            company = lookup.get(str(company_key))
            if not company:
                continue
            if company.get("company_name") and not item.get("company_name"):
                item["company_name"] = company.get("company_name")
            if company.get("industry") and not item.get("industry"):
                item["industry"] = company.get("industry")
            if company.get("sector"):
                item["sector"] = company.get("sector")
            if company.get("sector_resolution_status"):
                item["sector_resolution_status"] = company.get("sector_resolution_status")
            if company.get("market_cap") is not None:
                item["market_cap"] = company.get("market_cap")
            if company.get("profile_status") and not item.get("profile_status"):
                item["profile_status"] = company.get("profile_status")
            if company.get("profile_reason") and not item.get("profile_reason"):
                item["profile_reason"] = company.get("profile_reason")
        return lookup

    def _score_and_mark_clean_candidates(
        self,
        trades: list[dict[str, Any]],
        company_lookup_by_key: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        lookup = company_lookup_by_key or {}
        for item in trades:
            self._apply_trade_republic_match(item)

            company_key = item.get("company_key")
            if company_key:
                comp = lookup.get(str(company_key))
                if comp:
                    if comp.get("sector"):
                        item["sector"] = comp.get("sector")
                    if comp.get("sector_resolution_status"):
                        item["sector_resolution_status"] = comp.get("sector_resolution_status")
                    if comp.get("market_cap") is not None:
                        item["market_cap"] = comp.get("market_cap")

            symbol_value = str(item.get("symbol") or item.get("symbol_at_trade") or "").strip()
            dedupe_value = str(item.get("dedupe_key") or "").strip()
            validation_status = str(item.get("validation_status") or "").upper()
            processing_status = str(item.get("processing_status") or "").upper()
            try:
                qty_numeric = float(item.get("qty") or 0)
            except (TypeError, ValueError):
                qty_numeric = 0.0
            try:
                price_numeric = float(item.get("price") or 0)
            except (TypeError, ValueError):
                price_numeric = 0.0

            is_invalid_clean = (
                not dedupe_value
                or not symbol_value
                or qty_numeric <= 0
                or price_numeric <= 0
                or validation_status in {"INVALID", "PRICE_INVALID"}
                or processing_status == "VALIDATION_FAILED"
            )

            if is_invalid_clean:
                item["score"] = 0
                item["score_value"] = 0
                item["score_class"] = "E"
                item["core_insider_score"] = 0
                item["investability_score"] = 0
                item["execution_score"] = 0
                item["trade_republic_score"] = 0
                item["final_score"] = 0
                item["final_class"] = "E"
                item["decision_status"] = "INVALID"
                item["dashboard_valid"] = False
                item["processing_status"] = "VALIDATION_FAILED"
                continue

            try:
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
                item["dashboard_valid"] = self._is_dashboard_valid(item)
            except Exception:
                LOGGER.exception("Scoring fehlgeschlagen fuer dedupe_key=%s", item.get("dedupe_key"))
                item["decision_status"] = "REVIEW"
                item["score"] = 0
                item["score_value"] = 0
                item["score_class"] = "E"
                item["core_insider_score"] = 0
                item["investability_score"] = 0
                item["execution_score"] = 0
                item["trade_republic_score"] = 0
                item["final_score"] = 0
                item["final_class"] = "E"
                item["dashboard_valid"] = False

            if str(item.get("validation_status") or "").upper() in {"INVALID", "PRICE_INVALID"}:
                item["processing_status"] = "VALIDATION_FAILED"
            elif str(item.get("gate_status") or "").upper() == GATE_PASS:
                item["processing_status"] = "CLEAN_UPSERTED"
            elif str(item.get("gate_status") or "").upper() in {"PRE_GATE_FAIL", "FAIL"}:
                item["processing_status"] = "PRE_GATE_FAIL"

    @staticmethod
    def _build_clean_upsert_batch(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            item
            for item in trades
            if str(item.get("processing_status") or "").upper() != "VALIDATION_FAILED"
            and str(item.get("dedupe_key") or "").strip()
        ]

    def _prepare_raw_trade_for_sync(self, raw_row: dict[str, Any], fetched_at: datetime) -> dict[str, Any]:
        row = dict(raw_row or {})
        row_payload = row.get("raw_payload")

        has_normalized_shape = bool(row.get("filing_date") and row.get("transaction_date") and (row.get("symbol") or row.get("symbol_at_trade")))
        has_fmp_shape = any(key in row for key in ("filingDate", "transactionDate", "acquisitionOrDisposition", "securitiesTransacted", "transactionType"))
        has_payload_fmp_shape = isinstance(row_payload, dict) and any(
            key in row_payload for key in ("filingDate", "transactionDate", "acquisitionOrDisposition", "securitiesTransacted", "transactionType")
        )

        if has_normalized_shape:
            prepared = dict(row)
        elif has_fmp_shape:
            prepared = normalize_insider_trade(row, fetched_at=fetched_at)
        elif has_payload_fmp_shape:
            payload_dict = dict(row_payload) if isinstance(row_payload, dict) else {}
            prepared = normalize_insider_trade(payload_dict, fetched_at=fetched_at)
            for key in ("dedupe_key", "company_key", "symbol", "symbol_at_trade"):
                if row.get(key):
                    prepared[key] = row.get(key)
        else:
            prepared = dict(row)

        symbol = str(prepared.get("symbol") or prepared.get("symbol_at_trade") or "").strip().upper()
        prepared["symbol"] = symbol or None
        prepared["symbol_at_trade"] = symbol or prepared.get("symbol_at_trade")

        filing_date = prepared.get("filing_date")
        if filing_date is not None and not hasattr(filing_date, "date"):
            prepared["filing_date"] = parse_datetime(filing_date, "filing_date")
        transaction_date = prepared.get("transaction_date")
        if transaction_date is not None and not hasattr(transaction_date, "date"):
            prepared["transaction_date"] = parse_datetime(transaction_date, "transaction_date")

        qty = parse_float(prepared.get("qty"), "qty")
        price = parse_float(prepared.get("price"), "price")
        prepared["qty"] = qty
        prepared["price"] = price

        if prepared.get("trade_value_estimated") is None and qty is not None and price is not None and price > 0:
            prepared["trade_value_estimated"] = qty * price
        if prepared.get("trade_value") is None:
            prepared["trade_value"] = prepared.get("trade_value_estimated")

        if not prepared.get("acquisition_or_disposition"):
            direction = str(prepared.get("direction") or "").strip().upper()
            if direction == "BUY":
                prepared["acquisition_or_disposition"] = "A"
            elif direction == "SELL":
                prepared["acquisition_or_disposition"] = "D"

        if not prepared.get("form_type") and row.get("formType"):
            prepared["form_type"] = row.get("formType")

        prepared.setdefault("validation_status", "VALID")
        if price is not None and price <= 0:
            prepared["validation_status"] = "PRICE_INVALID"

        prepared.setdefault("profile_status", "NOT_REQUESTED")
        prepared.setdefault("profile_reason", None)
        prepared.setdefault("tr_availability_state", "UNKNOWN")
        prepared.setdefault("tr_tradability_state", "UNKNOWN")
        prepared.setdefault("tr_match_confidence", "LOW")
        prepared.setdefault("fetched_at", fetched_at)
        prepared.setdefault("first_seen_at", fetched_at)
        prepared.setdefault("last_seen_at", fetched_at)
        return prepared

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

    def _upsert_company_stub(self, trade: dict[str, Any], fetched_at: datetime) -> dict[str, Any] | None:
        """Kompatibilitäts-Helper für bestehende Tests und fokussierte Stub-Persistenz."""
        company_stub = self._build_company_stub(trade, fetched_at)
        if company_stub is None:
            return None
        self._persist_company_batch([company_stub])
        return company_stub

    def _persist_company_batch(self, companies: list[dict[str, Any]]) -> None:
        if hasattr(self.company_mongo_repo, "upsert_profiles"):
            self.company_mongo_repo.upsert_profiles(companies)
        elif hasattr(self.company_mongo_repo, "upsert_profile"):
            for company in companies:
                self.company_mongo_repo.upsert_profile(company)
        if self.company_mysql_repo is not None:
            if hasattr(self.company_mysql_repo, "upsert_companies"):
                self.company_mysql_repo.upsert_companies(companies)
            else:
                for company in companies:
                    self.company_mysql_repo.upsert_company(company)

    def _update_company_trade_stats(self, trades: list[dict[str, Any]]) -> None:
        """
        Aktualisiert company_trade_stats DETERMINISTISCH (nicht deltabasiert).

        Problem (vorher): Delta-Inkremente führten zu Overcounting bei wiederholten Imports
        mit überlappenden Trades, da upsert_trades() auch bei Duplikaten (dedupe_key) diese
        berücksichtigt.

        Lösung: Nach dem Trade-Upsert die betroffenen Firmen deterministisch aus
        insider_trades neu berechnen und company_trade_stats ersetzen.
        """
        if self.company_mysql_repo is None:
            return

        # Sammle die company_keys aus den aktuellen Trades
        company_keys_to_recompute = {
            str(trade.get("company_key") or "").strip()
            for trade in trades
            if trade.get("company_key")
        }
        if not company_keys_to_recompute:
            return

        if not hasattr(self.company_mysql_repo, "recompute_trade_stats_for_company_keys"):
            LOGGER.warning("company_trade_stats Recompute-Methode fehlt; Stats-Update wird ausgelassen.")
            return
        self.company_mysql_repo.recompute_trade_stats_for_company_keys(sorted(company_keys_to_recompute))

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
        try:
            price = float(trade.get("price") or 0)
        except (TypeError, ValueError):
            price = 0.0
        if price <= 0:
            return False
            
        # 3. Qty gültig
        try:
            qty = float(trade.get("qty") or 0)
        except (TypeError, ValueError):
            qty = 0.0
        if qty <= 0:
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
