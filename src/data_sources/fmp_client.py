"""API-Client für die im MVP freigegebenen FMP-Endpunkte."""

from __future__ import annotations

import logging
from typing import Any

import requests

from src.config.settings import (
    LATEST_INSIDER_ENDPOINT,
    PROFILE_ENDPOINT,
    FmpConfig,
    validate_fmp_api_key,
)

LOGGER = logging.getLogger(__name__)


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
        response = requests.get(
            f"{self.config.base_url}{LATEST_INSIDER_ENDPOINT}",
            params=params,
            timeout=self.timeout_seconds,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            LOGGER.exception("FMP-Feed konnte nicht geladen werden: %s", exc)
            raise

        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Unerwartetes Antwortformat für Latest Insider Trading.")
        return payload

    def fetch_company_profile(self, symbol: str) -> dict[str, Any] | None:
        """Lädt das Unternehmensprofil für ein Symbol.

        Args:
            symbol: Börsensymbol.

        Returns:
            dict[str, Any] | None: Profilobjekt oder None bei leerer Antwort.
        """

        params = {"symbol": symbol, "apikey": self.config.api_key}
        response = requests.get(
            f"{self.config.base_url}{PROFILE_ENDPOINT}",
            params=params,
            timeout=self.timeout_seconds,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            LOGGER.exception("FMP-Profil konnte nicht geladen werden (%s): %s", symbol, exc)
            raise

        payload = response.json()
        if isinstance(payload, list):
            return payload[0] if payload else None
        if isinstance(payload, dict):
            return payload
        raise ValueError(f"Unerwartetes Antwortformat für Company Profile ({symbol}).")
