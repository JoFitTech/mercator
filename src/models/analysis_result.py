"""Leichtgewichtiges Analysemodell für UI-Ausgaben."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AnalysisResult:
    """Strukturiert Kennzahlen und Zusatzdaten für Dashboard und Detailansichten."""

    title: str
    metrics: dict[str, Any] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)
    raw_rows: list[dict[str, Any]] = field(default_factory=list)
    company_profile: dict[str, Any] = field(default_factory=dict)
    note: str = ""
