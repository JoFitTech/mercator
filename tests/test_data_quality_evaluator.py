from __future__ import annotations

from datetime import datetime, timezone

from src.preprocessing.data_quality_evaluator import (
    QUALITY_FAILED,
    QUALITY_INCOMPLETE,
    QUALITY_MISSING,
    QUALITY_READY,
    QUALITY_STALE,
    QUALITY_UNKNOWN,
    assess_data_quality,
    build_data_quality_message,
    data_quality_status_label,
    data_quality_status_to_semantic,
    normalize_data_quality_status,
)


def test_normalize_data_quality_status_maps_common_synonyms() -> None:
    assert normalize_data_quality_status("success") == QUALITY_READY
    assert normalize_data_quality_status("not_requested") == QUALITY_MISSING
    assert normalize_data_quality_status("partial_success") == QUALITY_INCOMPLETE
    assert normalize_data_quality_status("rate_limited") == QUALITY_FAILED
    assert normalize_data_quality_status("outdated") == QUALITY_STALE
    assert normalize_data_quality_status("") == QUALITY_UNKNOWN


def test_data_quality_message_uses_visible_text_and_reason() -> None:
    message = build_data_quality_message(
        "stale",
        data_category="historical_price",
        reason="last update 10 days ago",
    )

    assert "Kursdaten" in message
    assert "veraltet" in message
    assert "last update 10 days ago" in message


def test_data_quality_assessment_returns_label_and_semantic() -> None:
    assessment = assess_data_quality(
        "partial",
        data_category="company_profile",
        reason="provider returned only name and exchange",
        source_refreshed_at=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
    )

    assert assessment.status == QUALITY_INCOMPLETE
    assert assessment.label == "Unvollstaendig"
    assert assessment.severity == "warning"
    assert assessment.category == "Profil"
    assert assessment.message.endswith(".")
    assert data_quality_status_label("failed") == "Fehlgeschlagen"
    assert data_quality_status_to_semantic("failed") == "error"

