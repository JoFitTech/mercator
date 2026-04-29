from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Any

from src.domain.trade_republic_universe import TradeRepublicUniverseSourcePayload


class TradeRepublicUniverseSource:
    def __init__(self, settings: Any) -> None:
        self.settings = settings

    def resolve_local_csv_path(self, path: str | Path | None = None) -> Path:
        raw_path = str(path or getattr(self.settings, "trade_republic_universe_local_csv", "") or "").strip()
        if not raw_path:
            raise ValueError("TRADE_REPUBLIC_UNIVERSE_LOCAL_CSV ist leer.")

        resolved = Path(raw_path)
        project_root = getattr(self.settings, "project_root", None)
        if not resolved.is_absolute() and project_root:
            resolved = Path(str(project_root)) / resolved
        return resolved

    def fetch_local_csv(self, path: str | Path | None = None) -> TradeRepublicUniverseSourcePayload:
        resolved = self.resolve_local_csv_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Trade-Republic-CSV nicht gefunden: {resolved}")

        content = resolved.read_bytes()
        if not content.strip():
            raise ValueError(f"Trade-Republic-CSV ist leer: {resolved}")

        fetched_at = datetime.now(UTC)
        return TradeRepublicUniverseSourcePayload(
            content=content,
            content_type="text/csv",
            source_url=str(resolved),
            source_type="local_csv",
            fetched_at=fetched_at,
            source_hash=hashlib.sha256(memoryview(content)).hexdigest(),
        )

    def fetch(self) -> TradeRepublicUniverseSourcePayload:
        return self.fetch_local_csv()

