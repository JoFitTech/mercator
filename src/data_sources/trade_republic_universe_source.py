from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Any

import requests

from src.domain.trade_republic_universe import TradeRepublicUniverseSourcePayload


class TradeRepublicUniverseSource:
    def __init__(self, settings: Any) -> None:
        self.settings = settings

    def fetch(self, mode_override: str | None = None) -> TradeRepublicUniverseSourcePayload:
        mode = str(mode_override or getattr(self.settings, "trade_republic_universe_source_mode", "local_csv") or "local_csv").strip().lower()
        if mode == "local_csv":
            return self._fetch_local_csv()
        if mode in {"remote_csv", "remote_pdf"}:
            return self._fetch_remote(mode)
        raise ValueError(f"Unbekannter TR-Source-Mode: {mode}")

    def _fetch_local_csv(self) -> TradeRepublicUniverseSourcePayload:
        raw_path = str(getattr(self.settings, "trade_republic_universe_local_csv", "") or "").strip()
        if not raw_path:
            raise ValueError("TRADE_REPUBLIC_UNIVERSE_LOCAL_CSV ist leer.")

        path = Path(raw_path)
        project_root = getattr(self.settings, "project_root", None)
        if not path.is_absolute() and project_root:
            path = Path(project_root) / path

        content = path.read_bytes()
        source_url = str(path)
        fetched_at = datetime.now(UTC)
        return TradeRepublicUniverseSourcePayload(
            content=content,
            content_type="text/csv",
            source_url=source_url,
            source_type="local_csv",
            fetched_at=fetched_at,
            source_hash=hashlib.sha256(content).hexdigest(),
        )

    def _fetch_remote(self, mode: str) -> TradeRepublicUniverseSourcePayload:
        if not bool(getattr(self.settings, "trade_republic_allow_remote_refresh", False)):
            raise PermissionError("Remote-Refresh ist deaktiviert (TRADE_REPUBLIC_ALLOW_REMOTE_REFRESH=false).")

        source_url = str(getattr(self.settings, "trade_republic_universe_url", "") or "").strip()
        if not source_url:
            raise ValueError("TRADE_REPUBLIC_UNIVERSE_URL ist leer.")

        response = requests.get(source_url, timeout=30)
        response.raise_for_status()
        content = response.content
        fetched_at = datetime.now(UTC)
        return TradeRepublicUniverseSourcePayload(
            content=content,
            content_type=response.headers.get("Content-Type"),
            source_url=source_url,
            source_type=mode,
            fetched_at=fetched_at,
            source_hash=hashlib.sha256(content).hexdigest(),
        )

