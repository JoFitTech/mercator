"""Services für Trade-Republic-Universum (offizielle Referenzdaten + Matching)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import csv
import hashlib
import io
import logging
import re
from typing import Any

import requests

from src.config.settings import AppSettings
from src.db.mysql_client import MySqlClient

LOGGER = logging.getLogger(__name__)

TR_STATUS_IN = "IN_UNIVERSE"
TR_STATUS_NOT_IN = "NOT_IN_UNIVERSE"
TR_STATUS_UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class TradeRepublicUniverseInstrument:
    isin: str
    symbol: str | None
    instrument_name: str | None
    country: str | None
    asset_class: str | None


@dataclass(slots=True)
class TradeRepublicMatchResult:
    status: str
    match_method: str
    match_confidence: str
    source_refreshed_at: datetime | None
    reference_isin: str | None
    reference_name: str | None


class TradeRepublicUniverseIngestionService:
    """Lädt und persistiert das offizielle TR-Instrument-Universum."""

    def __init__(self, settings: AppSettings, mysql_client: MySqlClient | None) -> None:
        self.settings = settings
        self.mysql_client = mysql_client

    def refresh_if_stale(self, force: bool = False) -> tuple[bool, str]:
        if self.mysql_client is None:
            return False, "mysql_unavailable"
        try:
            with self.mysql_client.connection() as conn:
                with conn.cursor(dictionary=True) as cur:
                    cur.execute(
                        "SELECT source_last_refreshed_at FROM trade_republic_universe_meta "
                        "WHERE source_url = %s LIMIT 1",
                        (self.settings.trade_republic_universe_url,),
                    )
                    row = cur.fetchone()
                    if not force and row and row.get("source_last_refreshed_at"):
                        refreshed_at = row["source_last_refreshed_at"]
                        if isinstance(refreshed_at, datetime):
                            age = datetime.now(UTC) - refreshed_at.replace(tzinfo=UTC)
                            if age < timedelta(hours=self.settings.trade_republic_refresh_ttl_hours):
                                return False, "cache_fresh"
        except Exception:
            LOGGER.exception("TR universe stale-check fehlgeschlagen.")

        try:
            response = requests.get(self.settings.trade_republic_universe_url, timeout=30)
            response.raise_for_status()
            payload = response.text
            parsed = self.parse_universe_csv(payload)
            self._store_snapshot(parsed, source_payload=payload)
            return True, "refreshed"
        except Exception:
            LOGGER.exception("TR universe refresh fehlgeschlagen.")
            return False, "refresh_failed"

    @staticmethod
    def parse_universe_csv(raw_text: str) -> list[TradeRepublicUniverseInstrument]:
        if not raw_text.strip():
            return []
        reader = csv.DictReader(io.StringIO(raw_text))
        items: list[TradeRepublicUniverseInstrument] = []
        for row in reader:
            isin = str(row.get("isin") or row.get("ISIN") or "").strip().upper()
            if not isin:
                continue
            symbol = str(row.get("symbol") or row.get("ticker") or row.get("Symbol") or "").strip().upper() or None
            name = str(row.get("instrument_name") or row.get("name") or row.get("Name") or "").strip() or None
            country = str(row.get("country") or row.get("Country") or "").strip() or None
            asset_class = str(row.get("asset_class") or row.get("type") or row.get("Type") or "").strip() or None
            items.append(
                TradeRepublicUniverseInstrument(
                    isin=isin,
                    symbol=symbol,
                    instrument_name=name,
                    country=country,
                    asset_class=asset_class,
                )
            )
        return items

    def _store_snapshot(self, items: list[TradeRepublicUniverseInstrument], source_payload: str) -> None:
        if self.mysql_client is None:
            return
        refreshed_at = datetime.now(UTC).replace(tzinfo=None)
        snapshot_hash = hashlib.sha256(source_payload.encode("utf-8")).hexdigest()
        with self.mysql_client.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM trade_republic_universe_reference")
                for item in items:
                    cur.execute(
                        """
                        INSERT INTO trade_republic_universe_reference
                        (isin, symbol, instrument_name, country, asset_class, source_url, source_last_refreshed_at, source_hash)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            item.isin,
                            item.symbol,
                            item.instrument_name,
                            item.country,
                            item.asset_class,
                            self.settings.trade_republic_universe_url,
                            refreshed_at,
                            snapshot_hash,
                        ),
                    )
                cur.execute(
                    """
                    INSERT INTO trade_republic_universe_meta
                    (source_url, source_last_refreshed_at, source_hash, instrument_count, last_error)
                    VALUES (%s,%s,%s,%s,NULL)
                    ON DUPLICATE KEY UPDATE
                        source_last_refreshed_at = VALUES(source_last_refreshed_at),
                        source_hash = VALUES(source_hash),
                        instrument_count = VALUES(instrument_count),
                        last_error = NULL
                    """,
                    (self.settings.trade_republic_universe_url, refreshed_at, snapshot_hash, len(items)),
                )
            conn.commit()


class TradeRepublicUniverseMatchingService:
    """Ordnet Firmen/Trades defensiv dem TR-Universum zu."""

    def __init__(self, mysql_client: MySqlClient | None) -> None:
        self.mysql_client = mysql_client

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
                cur.execute(
                    "SELECT source_last_refreshed_at FROM trade_republic_universe_meta LIMIT 1"
                )
                meta = cur.fetchone() or {}
                refreshed_at = meta.get("source_last_refreshed_at")

                if isin:
                    cur.execute(
                        "SELECT isin, instrument_name FROM trade_republic_universe_reference WHERE isin = %s LIMIT 1",
                        (isin,),
                    )
                    by_isin = cur.fetchone()
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
                    candidates = cur.fetchall() or []
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

        return TradeRepublicMatchResult(TR_STATUS_UNKNOWN, "NONE", "LOW", None, None, None)
