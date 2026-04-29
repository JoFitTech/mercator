"""Services für Trade-Republic-Universum (statische Referenzdaten + Matching)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import re

from src.config.settings import AppSettings
from src.data_sources.trade_republic_universe_source import TradeRepublicUniverseSource
from src.db.mysql_client import MySqlClient
from src.db.repositories.trade_republic_universe_repository import TradeRepublicUniverseRepository
from src.domain.trade_republic_universe import (
    TradeRepublicUniverseImportSummary,
    TradeRepublicUniverseParseResult,
)
from src.preprocessing.trade_republic_universe_parser import parse_trade_republic_csv

LOGGER = logging.getLogger(__name__)

TR_STATUS_IN = "IN_UNIVERSE"
TR_STATUS_NOT_IN = "NOT_IN_UNIVERSE"
TR_STATUS_UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class TradeRepublicMatchResult:
    status: str
    match_method: str
    match_confidence: str
    source_refreshed_at: datetime | None
    reference_isin: str | None
    reference_name: str | None


class TradeRepublicUniverseIngestionService:
    """Lädt und persistiert das TR-Universum kontrolliert (Admin/Seed)."""

    def __init__(self, settings: AppSettings, mysql_client: MySqlClient | None) -> None:
        self.settings = settings
        self.mysql_client = mysql_client
        self._source = TradeRepublicUniverseSource(settings)
        self._repo = TradeRepublicUniverseRepository(mysql_client)

    @staticmethod
    def parse_universe_csv(raw_text: str) -> TradeRepublicUniverseParseResult:
        # Kompatibilitäts-Fassade für bestehende Tests/Aufrufer.
        return parse_trade_republic_csv(raw_text)

    def import_local_csv(self, force: bool = True) -> TradeRepublicUniverseImportSummary:
        try:
            source_path = str(self._source.resolve_local_csv_path())
        except Exception:
            source_path = str(self.settings.trade_republic_universe_local_csv or "")
        if self.mysql_client is None:
            return TradeRepublicUniverseImportSummary(
                status="mysql_unavailable",
                source_url=source_path,
                source_type="none",
                total_rows=0,
                valid_rows=0,
                invalid_rows=0,
                inserted_rows=0,
                source_hash="",
                refreshed_at=None,
                error="MySQL nicht verfügbar.",
            )

        if (not force) and (not self._repo.is_stale(source_path, int(self.settings.trade_republic_refresh_ttl_hours))):
            meta = self._repo.get_meta(source_path)
            return TradeRepublicUniverseImportSummary(
                status="cache_fresh",
                source_url=source_path,
                source_type="local_csv",
                total_rows=int(meta.get("instrument_count", 0) or 0),
                valid_rows=int(meta.get("instrument_count", 0) or 0),
                invalid_rows=int(meta.get("invalid_rows", 0) or 0),
                inserted_rows=int(meta.get("instrument_count", 0) or 0),
                source_hash=str(meta.get("source_hash") or ""),
                refreshed_at=meta.get("source_last_refreshed_at"),
            )

        try:
            payload = self._source.fetch_local_csv()
            parsed = parse_trade_republic_csv(payload.content.decode("utf-8", errors="replace"))

            if parsed.valid_rows <= 0:
                raise ValueError("Trade-Republic-CSV enthält keine gültigen Instrumente.")

            self._repo.replace_snapshot(
                parsed.instruments,
                {
                    "source_url": payload.source_url,
                    "source_type": "local_csv",
                    "source_last_refreshed_at": payload.fetched_at.astimezone(UTC).replace(tzinfo=None),
                    "source_hash": payload.source_hash,
                    "valid_rows": parsed.valid_rows,
                    "invalid_rows": parsed.invalid_rows,
                    "last_import_status": "SUCCESS",
                },
            )
            return TradeRepublicUniverseImportSummary(
                status="refreshed",
                source_url=payload.source_url,
                source_type=payload.source_type,
                total_rows=parsed.total_rows,
                valid_rows=parsed.valid_rows,
                invalid_rows=parsed.invalid_rows,
                inserted_rows=parsed.valid_rows,
                source_hash=payload.source_hash,
                refreshed_at=payload.fetched_at,
            )
        except Exception as exc:
            LOGGER.exception("TR universe local CSV import fehlgeschlagen.")
            self._repo.store_error(source_url=source_path, error_text=str(exc))
            return TradeRepublicUniverseImportSummary(
                status="refresh_failed",
                source_url=source_path,
                source_type="local_csv",
                total_rows=0,
                valid_rows=0,
                invalid_rows=0,
                inserted_rows=0,
                source_hash="",
                refreshed_at=None,
                error=str(exc),
            )

    def refresh(self, force: bool = True) -> TradeRepublicUniverseImportSummary:
        return self.import_local_csv(force=force)

    def refresh_if_stale(self, force: bool = False) -> tuple[bool, str]:
        summary = self.import_local_csv(force=force)
        return summary.status == "refreshed", summary.status

    def refresh_from_local_csv(self) -> TradeRepublicUniverseImportSummary:
        return self.import_local_csv(force=True)


class TradeRepublicUniverseMatchingService:
    """Ordnet Firmen/Trades defensiv dem TR-Universum zu."""

    def __init__(self, mysql_client: MySqlClient | None) -> None:
        self.mysql_client = mysql_client
        self._repo = TradeRepublicUniverseRepository(mysql_client)

    @staticmethod
    def _normalize_name(value: str | None) -> str:
        if not value:
            return ""
        return re.sub(r"[^A-Z0-9]+", "", value.upper())

    def match_company(
        self,
        company_isin: str | None,
        symbol: str | None,
        company_name: str | None,
    ) -> TradeRepublicMatchResult:
        if self.mysql_client is None:
            return TradeRepublicMatchResult(TR_STATUS_UNKNOWN, "NONE", "LOW", None, None, None)

        isin = str(company_isin or "").strip().upper()
        sym = str(symbol or "").strip().upper()
        normalized_name = self._normalize_name(company_name)

        with self.mysql_client.connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT source_last_refreshed_at FROM trade_republic_universe_meta LIMIT 1")
                raw_meta = cur.fetchone()
                meta = raw_meta if isinstance(raw_meta, dict) else {}
                refreshed_at = meta.get("source_last_refreshed_at")

                if isin:
                    cur.execute(
                        "SELECT isin, instrument_name FROM trade_republic_universe_reference WHERE isin = %s LIMIT 1",
                        (isin,),
                    )
                    raw_by_isin = cur.fetchone()
                    by_isin = raw_by_isin if isinstance(raw_by_isin, dict) else None
                    if by_isin:
                        return TradeRepublicMatchResult(
                            TR_STATUS_IN,
                            "ISIN",
                            "HIGH",
                            refreshed_at,
                            by_isin.get("isin"),
                            by_isin.get("instrument_name"),
                        )
                    if refreshed_at:
                        return TradeRepublicMatchResult(TR_STATUS_NOT_IN, "NONE", "HIGH", refreshed_at, None, None)

                if sym and normalized_name:
                    cur.execute(
                        "SELECT isin, instrument_name FROM trade_republic_universe_reference WHERE symbol = %s",
                        (sym,),
                    )
                    raw_candidates = cur.fetchall() or []
                    candidates = [row for row in raw_candidates if isinstance(row, dict)]
                    matching_name = [
                        row for row in candidates
                        if self._normalize_name(str(row.get("instrument_name") or "")) == normalized_name
                    ]
                    if len(matching_name) == 1:
                        row = matching_name[0]
                        return TradeRepublicMatchResult(
                            TR_STATUS_IN,
                            "SYMBOL_AND_NAME",
                            "MEDIUM",
                            refreshed_at,
                            row.get("isin"),
                            row.get("instrument_name"),
                        )
                    if len(candidates) == 0 and refreshed_at:
                        return TradeRepublicMatchResult(TR_STATUS_NOT_IN, "NONE", "MEDIUM", refreshed_at, None, None)

        LOGGER.info("TR match fallback UNKNOWN symbol=%s isin=%s", sym, isin)
        return TradeRepublicMatchResult(TR_STATUS_UNKNOWN, "NONE", "LOW", None, None, None)


