"""Helper fuer sichtbare Datenqualitaets-Status und Textmaerkmalen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

QUALITY_READY = "READY"
QUALITY_MISSING = "MISSING"
QUALITY_STALE = "STALE"
QUALITY_INCOMPLETE = "INCOMPLETE"
QUALITY_LOW_QUALITY = "LOW_QUALITY"
QUALITY_FAILED = "FAILED"
QUALITY_UNKNOWN = "UNKNOWN"

_STATUS_LABELS = {
    QUALITY_READY: "Bereit",
    QUALITY_MISSING: "Fehlt",
    QUALITY_STALE: "Veraltet",
    QUALITY_INCOMPLETE: "Unvollstaendig",
    QUALITY_LOW_QUALITY: "Niedrige Qualitaet",
    QUALITY_FAILED: "Fehlgeschlagen",
    QUALITY_UNKNOWN: "Unbekannt",
}

_STATUS_SEMANTICS = {
    QUALITY_READY: "success",
    QUALITY_MISSING: "warning",
    QUALITY_STALE: "warning",
    QUALITY_INCOMPLETE: "warning",
    QUALITY_LOW_QUALITY: "warning",
    QUALITY_FAILED: "error",
    QUALITY_UNKNOWN: "info",
}

_STATUS_ALIASES = {
    QUALITY_READY: {"READY", "SUCCESS", "PASS", "VALID", "COMPLETE", "AVAILABLE", "FETCHED", "OK"},
    QUALITY_MISSING: {"MISSING", "NOT_FOUND", "NOT_REQUESTED", "UNRESOLVED", "NO_DATA", "ABSENT"},
    QUALITY_STALE: {"STALE", "OUTDATED", "EXPIRED", "OLD"},
    QUALITY_INCOMPLETE: {"INCOMPLETE", "PARTIAL", "PARTIALLY_AVAILABLE", "PARTIAL_SUCCESS"},
    QUALITY_LOW_QUALITY: {"LOW_QUALITY", "LOW", "POOR", "QUESTIONABLE", "NOISY"},
    QUALITY_FAILED: {"FAILED", "FAIL", "ERROR", "RATE_LIMITED", "UNAUTHORIZED", "TIMEOUT", "INVALID", "BLOCKED"},
}

_CATEGORY_LABELS = {
    "company_profile": "Profil",
    "historical_price": "Kursdaten",
    "financial_metric": "Finanzdaten",
    "financial_metrics": "Finanzdaten",
    "valuation_metric": "Bewertungsdaten",
    "feature": "Featuredaten",
    "technical_features": "Technische Features",
    "fundamental_features": "Fundamentaldaten",
    "model_run": "Modelllauf",
    "prediction": "Prognose",
    "backtest": "Backtest",
    "preference_score": "Preference Score",
    "watchlist": "Watchlist",
}


@dataclass(slots=True)
class DataQualityAssessment:
    """Normalisierte Datenqualitaetsbewertung mit sichtbarem Text."""

    status: str
    label: str
    message: str
    severity: str
    category: str | None = None
    reason: str | None = None


def normalize_data_quality_status(value: Any) -> str:
    """Mappt beliebige Roh-Status auf die kanonischen Stock-Analysis-Qualitaetsstatus."""

    normalized = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    if not normalized:
        return QUALITY_UNKNOWN
    if normalized in _STATUS_LABELS:
        return normalized
    for canonical, aliases in _STATUS_ALIASES.items():
        if normalized in aliases:
            return canonical
    return QUALITY_UNKNOWN


def data_quality_status_label(value: Any) -> str:
    status = normalize_data_quality_status(value)
    return _STATUS_LABELS.get(status, status.title() if status else "Unbekannt")


def data_quality_status_to_semantic(value: Any) -> str:
    status = normalize_data_quality_status(value)
    return _STATUS_SEMANTICS.get(status, "info")


def _friendly_category_label(value: Any | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    mapped = _CATEGORY_LABELS.get(normalized.lower())
    if mapped:
        return mapped
    return normalized.replace("_", " ")


def build_data_quality_message(
    status: Any,
    data_category: Any | None = None,
    reason: Any | None = None,
    source_refreshed_at: datetime | None = None,
) -> str:
    """Erzeugt einen sichtbaren, nicht-icon-basierten Datenqualitaetstext."""

    canonical = normalize_data_quality_status(status)
    category_label = _friendly_category_label(data_category)
    if category_label:
        base_messages = {
            QUALITY_READY: f"Daten fuer {category_label} sind bereit.",
            QUALITY_MISSING: f"Daten fuer {category_label} fehlen.",
            QUALITY_STALE: f"Daten fuer {category_label} sind veraltet.",
            QUALITY_INCOMPLETE: f"Daten fuer {category_label} sind unvollstaendig.",
            QUALITY_LOW_QUALITY: f"Daten fuer {category_label} haben niedrige Qualitaet.",
            QUALITY_FAILED: f"Daten fuer {category_label} sind fehlgeschlagen.",
            QUALITY_UNKNOWN: f"Status fuer {category_label} ist unbekannt.",
        }
    else:
        base_messages = {
            QUALITY_READY: "Daten sind bereit.",
            QUALITY_MISSING: "Daten fehlen.",
            QUALITY_STALE: "Daten sind veraltet.",
            QUALITY_INCOMPLETE: "Daten sind unvollstaendig.",
            QUALITY_LOW_QUALITY: "Daten haben niedrige Qualitaet.",
            QUALITY_FAILED: "Daten sind fehlgeschlagen.",
            QUALITY_UNKNOWN: "Datenstatus ist unbekannt.",
        }

    message = base_messages.get(canonical, base_messages[QUALITY_UNKNOWN])
    if reason:
        reason_text = str(reason).strip().rstrip(".")
        if reason_text:
            message = f"{message.rstrip('.')} ({reason_text})."
    if source_refreshed_at is not None:
        timestamp = source_refreshed_at.isoformat(sep=" ", timespec="seconds")
        message = f"{message.rstrip('.')} Letzte Aktualisierung: {timestamp}."
    return message


def assess_data_quality(
    status: Any,
    data_category: Any | None = None,
    reason: Any | None = None,
    source_refreshed_at: datetime | None = None,
) -> DataQualityAssessment:
    """Erzeugt eine normalisierte Datenqualitaetsbewertung fuer UI und Services."""

    canonical = normalize_data_quality_status(status)
    return DataQualityAssessment(
        status=canonical,
        label=data_quality_status_label(canonical),
        message=build_data_quality_message(
            canonical,
            data_category=data_category,
            reason=reason,
            source_refreshed_at=source_refreshed_at,
        ),
        severity=data_quality_status_to_semantic(canonical),
        category=_friendly_category_label(data_category),
        reason=str(reason).strip() if reason is not None and str(reason).strip() else None,
    )
