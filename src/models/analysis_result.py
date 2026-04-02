"""Domänenmodell für aggregierte Analyseergebnisse."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisResult:
    """Kapselt Ergebnisse, die im Dashboard oder Explorer angezeigt werden."""

    title: str
    metrics: dict[str, Any] = field(default_factory=dict)
    dataframe_rows: int = 0
    note: str = ""
