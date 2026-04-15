"""API-Client für die im MVP freigegebenen FMP-Endpunkte."""

from __future__ import annotations

import logging
from typing import Any

import requests

from src.config.settings import (
    LATEST_INSIDER_ENDPOINT,
    PROFILE_CIK_ENDPOINT,
    PROFILE_ENDPOINT,
    SEARCH_INSIDER_TRADES_ENDPOINT,
    FmpConfig,
    validate_fmp_api_key,
)

LOGGER = logging.getLogger(__name__)


class FmpApiError(Exception):
    """Fachliche Exception für Fehler im FMP-API-Client."""


class FmpClient:
    """Kapselt HTTP-Zugriffe auf Latest Insider Trading und Company Profile."""

    def __init__(self, config: FmpConfig, timeout_seconds: int = 15) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        validate_fmp_api_key(self.config.api_key)

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
