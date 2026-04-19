"""API-Client für die im MVP freigegebenen FMP-Endpunkte."""

from __future__ import annotations

import logging
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
        validate_fmp_api_key(self.config.api_key)

    def _track_call(self) -> None:
        """Registriert einen API-Aufruf beim Usage-Service."""
        if self.api_usage_service:
            self.api_usage_service.track_call(provider="fmp", limit=250)

    def fetch_latest_insider_trades(self, page: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Lädt den Latest-Insider-Feed.

        Args:
            page: Feed-Seite im Endpunkt (MVP standardmäßig 0).
            limit: Anzahl Datensätze (MVP standardmäßig 100).

        Returns:
            list[dict[str, Any]]: Rohobjekte aus der API.
        """

        params = {"page": page, "limit": limit, "apikey": self.config.api_key}
        try:
            self._track_call()
            response = requests.get(
                f"{self.config.base_url}{LATEST_INSIDER_ENDPOINT}",
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.exception("FMP-Feed konnte nicht geladen werden: %s", exc)
            raise FmpApiError(f"Verbindungsfehler zur FMP-API: {exc}") from exc

        payload = response.json()
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
        try:
            self._track_call()
            response = requests.get(
                f"{self.config.base_url}{PROFILE_ENDPOINT}",
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.exception("FMP-Profil konnte nicht geladen werden (%s): %s", symbol, exc)
            raise FmpApiError(f"Fehler beim Laden des Profils für {symbol}: {exc}") from exc

        payload = response.json()
        if isinstance(payload, list):
            return payload[0] if payload else None
        if isinstance(payload, dict):
            return payload
        raise FmpApiError(f"Unerwartetes Antwortformat für Company Profile ({symbol}).")

    def fetch_company_profile_by_cik(self, cik: str) -> dict[str, Any] | None:
        """Lädt das Unternehmensprofil primär über CIK."""
        params = {"cik": cik, "apikey": self.config.api_key}
        try:
            self._track_call()
            response = requests.get(
                f"{self.config.base_url}{PROFILE_CIK_ENDPOINT}",
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.exception("FMP-Profil-CIK konnte nicht geladen werden (%s): %s", cik, exc)
            raise FmpApiError(f"Fehler beim Laden des Profils für CIK {cik}: {exc}") from exc

        payload = response.json()
        if isinstance(payload, list):
            return payload[0] if payload else None
        if isinstance(payload, dict):
            return payload
        return None

    def search_insider_trades(self, symbol: str, page: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Optionaler, manueller Backfill je Firma."""
        params = {"symbol": symbol, "page": page, "limit": limit, "apikey": self.config.api_key}
        try:
            self._track_call()
            response = requests.get(
                f"{self.config.base_url}{SEARCH_INSIDER_TRADES_ENDPOINT}",
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.exception("FMP-Suche fehlgeschlagen für %s: %s", symbol, exc)
            raise FmpApiError(f"Fehler bei der Insider-Suche für {symbol}: {exc}") from exc

        payload = response.json()
        return payload if isinstance(payload, list) else []

    def fetch_insider_trades_by_reporting_name(self, name: str, page: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Sucht Insider-Trades nach dem Namen des Insiders."""
        params = {"reportingName": name, "page": page, "limit": limit, "apikey": self.config.api_key}
        try:
            self._track_call()
            response = requests.get(
                f"{self.config.base_url}{INSIDER_REPORTING_NAME_ENDPOINT}",
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.exception("FMP-Suche nach Name fehlgeschlagen für %s: %s", name, exc)
            raise FmpApiError(f"Fehler bei der Insider-Suche nach Name für {name}: {exc}") from exc

        payload = response.json()
        return payload if isinstance(payload, list) else []

    def fetch_cik_lookup(self, symbol: str) -> list[dict[str, Any]]:
        """Sucht nach CIK-Informationen für ein Symbol."""
        params = {"ticker": symbol, "apikey": self.config.api_key}
        try:
            self._track_call()
            response = requests.get(
                f"{self.config.base_url}{SEARCH_CIK_ENDPOINT}",
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.exception("FMP-CIK-Lookup fehlgeschlagen für %s: %s", symbol, exc)
            raise FmpApiError(f"Fehler beim CIK-Lookup für {symbol}: {exc}") from exc

        payload = response.json()
        return payload if isinstance(payload, list) else []

    def fetch_insider_trade_statistics(self, symbol: str) -> dict[str, Any]:
        """Vorbereitete Methode für Insider-Statistiken (MAY)."""
        params = {"symbol": symbol, "apikey": self.config.api_key}
        try:
            self._track_call()
            response = requests.get(
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
            response = requests.get(
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
