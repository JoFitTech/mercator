"""API-Client für Polygon.io Ticker Details."""

from __future__ import annotations

import logging
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)

class PolygonClient:
    """Kapselt HTTP-Zugriffe auf Polygon.io Ticker Details."""

    def __init__(self, api_key: str, timeout_seconds: int = 15) -> None:
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"
        self.timeout_seconds = timeout_seconds

    def fetch_ticker_details(self, symbol: str) -> dict[str, Any] | None:
        """Lädt Ticker-Details für ein Symbol (v3).

        Returns:
            dict[str, Any] | None: Details-Objekt oder None.
        """
        if not self.api_key:
            return None

        url = f"{self.base_url}/v3/reference/tickers/{symbol}"
        params = {"apiKey": self.api_key}
        
        try:
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            
            if payload.get("status") == "OK" and "results" in payload:
                return payload["results"]
            
            return None
        except requests.RequestException as exc:
            LOGGER.exception("Polygon konnte nicht geladen werden (%s): %s", symbol, exc)
            return None
