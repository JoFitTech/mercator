"""API-Client für Alpha Vantage OVERVIEW-Endpunkt."""

from __future__ import annotations

import logging
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)

class AlphaVantageClient:
    """Kapselt HTTP-Zugriffe auf Alpha Vantage Company OVERVIEW."""

    def __init__(self, api_key: str, timeout_seconds: int = 15) -> None:
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.timeout_seconds = timeout_seconds

    def fetch_company_overview(self, symbol: str) -> dict[str, Any] | None:
        """Lädt das Unternehmens-Overview für ein Symbol.

        Returns:
            dict[str, Any] | None: Overview-Objekt oder None bei Fehler/leerer Antwort.
        """
        if not self.api_key:
            return None

        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
            "apikey": self.api_key
        }
        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            
            # Alpha Vantage gibt oft eine leere Dict oder Fehlermeldungen im JSON zurück
            if not payload or "Note" in payload or "Error Message" in payload:
                LOGGER.warning("Alpha Vantage lieferte kein Ergebnis für %s: %s", symbol, payload)
                return None
                
            return payload
        except requests.RequestException as exc:
            LOGGER.exception("Alpha Vantage konnte nicht geladen werden (%s): %s", symbol, exc)
            return None
