"""API-Client für die im MVP freigegebenen FMP-Endpunkte."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from src.services.api_usage_service import ApiUsageService
from src.config.settings import (
    COMPANY_SCREENER_ENDPOINT,
    INSIDER_REPORTING_NAME_ENDPOINT,
    INSIDER_STATISTICS_ENDPOINT,
    LATEST_INSIDER_ENDPOINT,
    PROFILE_CIK_ENDPOINT,
    PROFILE_ENDPOINT,
    SEARCH_CIK_ENDPOINT,
    EXCHANGE_VARIANTS_ENDPOINT,
    SEARCH_INSIDER_TRADES_ENDPOINT,
    FmpConfig,
    validate_fmp_api_key,
)

LOGGER = logging.getLogger(__name__)


class FmpApiError(Exception):
    """Fachliche Exception für Fehler im FMP-API-Client."""


class FmpClient:
    """Kapselt HTTP-Zugriffe auf Latest Insider Trading und Company Profile."""

    def __init__(
        self,
        config: FmpConfig,
        timeout_seconds: int = 15,
        api_usage_service: ApiUsageService | None = None,
    ) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self.api_usage_service = api_usage_service
        self._session = requests.Session()
        validate_fmp_api_key(self.config.api_key)

    def _track_call(self) -> None:
        """Registriert einen API-Aufruf beim Usage-Service."""
        if self.api_usage_service:
            self.api_usage_service.track_call(provider="fmp", limit=250)

    def _request(self, endpoint: str, params: dict[str, Any], retries: int = 2) -> Any:
        if self.api_usage_service and not self.api_usage_service.can_make_call(provider="fmp", limit=250):
            raise FmpApiError("FMP Tagesbudget erschöpft (250 Calls).")
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                self._track_call()
                started_at = time.perf_counter()
                response = self._session.get(
                    f"{self.config.base_url}{endpoint}",
                    params=params,
                    timeout=self.timeout_seconds,
                )
                latency_ms = (time.perf_counter() - started_at) * 1000
                LOGGER.info(
                    "fmp_request endpoint=%s status=%s latency_ms=%.1f attempt=%s",
                    endpoint,
                    response.status_code,
                    latency_ms,
                    attempt + 1,
                )
                if response.status_code == 403:
                    raise FmpApiError("FMP API-Key ungültig oder gesperrt (HTTP 403).")
                if response.status_code == 429 and attempt < retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                if response.status_code == 530:
                    raise FmpApiError("Upstream-Verbindung fehlgeschlagen (HTTP 530).")
                if response.status_code >= 500 and attempt < retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                last_exc = exc
                if attempt >= retries:
                    break
                time.sleep(min(2 ** attempt, 8))
        raise FmpApiError(f"Verbindungsfehler zur FMP-API: {last_exc}")

    def fetch_latest_insider_trades(self, page: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Lädt den Latest-Insider-Feed.

        Args:
            page: Feed-Seite im Endpunkt (MVP standardmäßig 0).
            limit: Anzahl Datensätze (MVP standardmäßig 100).

        Returns:
            list[dict[str, Any]]: Rohobjekte aus der API.
        """

        params = {"page": page, "limit": limit, "apikey": self.config.api_key}
        payload = self._request(LATEST_INSIDER_ENDPOINT, params=params)
        if not isinstance(payload, list):
            raise FmpApiError("Unerwartetes Antwortformat für Latest Insider Trading.")
        return payload

    def fetch_company_profile(self, symbol: str) -> dict[str, Any] | None:
        """Lädt das Unternehmensprofil für ein Symbol.

        Args:
            symbol: Börsensymbol.

        Returns:
            dict[str, Any] | None: Profilobjekt oder None bei leerer Antwort.
        """

        params = {"symbol": symbol, "apikey": self.config.api_key}
        payload = self._request(PROFILE_ENDPOINT, params=params)
        if isinstance(payload, list):
            return payload[0] if payload else None
        if isinstance(payload, dict):
            return payload
        raise FmpApiError(f"Unerwartetes Antwortformat für Company Profile ({symbol}).")

    def fetch_company_profile_by_cik(self, cik: str) -> dict[str, Any] | None:
        """Lädt das Unternehmensprofil primär über CIK."""
        params = {"cik": cik, "apikey": self.config.api_key}
        payload = self._request(PROFILE_CIK_ENDPOINT, params=params)
        if isinstance(payload, list):
            return payload[0] if payload else None
        if isinstance(payload, dict):
            return payload
        return None

    def search_insider_trades(self, symbol: str, page: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Optionaler, manueller Backfill je Firma."""
        params = {"symbol": symbol, "page": page, "limit": limit, "apikey": self.config.api_key}
        payload = self._request(SEARCH_INSIDER_TRADES_ENDPOINT, params=params)
        return payload if isinstance(payload, list) else []

    def fetch_insider_trades_by_reporting_name(self, name: str, page: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Sucht Insider-Trades nach dem Namen des Insiders."""
        params = {"reportingName": name, "page": page, "limit": limit, "apikey": self.config.api_key}
        payload = self._request(INSIDER_REPORTING_NAME_ENDPOINT, params=params)
        return payload if isinstance(payload, list) else []

    def fetch_cik_lookup(self, symbol: str) -> list[dict[str, Any]]:
        """Sucht nach CIK-Informationen für ein Symbol."""
        params = {"ticker": symbol, "apikey": self.config.api_key}
        payload = self._request(SEARCH_CIK_ENDPOINT, params=params)
        return payload if isinstance(payload, list) else []

    def fetch_exchange_variants(self, symbol: str) -> list[dict[str, Any]]:
        """Gezielter API3-Call zur Exchange-/Listing-Auflösung."""
        params = {"symbol": symbol, "apikey": self.config.api_key}
        payload = self._request(EXCHANGE_VARIANTS_ENDPOINT, params=params)
        return payload if isinstance(payload, list) else []

    def fetch_insider_trade_statistics(self, symbol: str) -> dict[str, Any]:
        """Vorbereitete Methode für Insider-Statistiken (MAY)."""
        params = {"symbol": symbol, "apikey": self.config.api_key}
        try:
            self._track_call()
            response = self._session.get(
                f"{self.config.base_url}{INSIDER_STATISTICS_ENDPOINT}",
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.debug("Insider-Statistiken (optional) fehlgeschlagen für %s: %s", symbol, exc)
            return {}
        
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def fetch_company_screener(self, **kwargs) -> list[dict[str, Any]]:
        """Vorbereitete Methode für Company Screener (MAY)."""
        params = {**kwargs, "apikey": self.config.api_key}
        try:
            self._track_call()
            response = self._session.get(
                f"{self.config.base_url}{COMPANY_SCREENER_ENDPOINT}",
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.debug("Company Screener (optional) fehlgeschlagen: %s", exc)
            return []
        
        payload = response.json()
        return payload if isinstance(payload, list) else []
