from __future__ import annotations

from src.ui.components.formatting import format_empty, format_score
from src.ui.components.status_badges import status_to_label, status_to_semantic_color


def test_format_empty_replaces_none_and_nan_like_values() -> None:
    assert format_empty(None) == "—"
    assert format_empty("None") == "—"
    assert format_empty("nan") == "—"


def test_format_score_replaces_missing_with_dash() -> None:
    assert format_score(None) == "—"
    assert format_score(72.35) == "72.4"


def test_status_badge_mapping_has_clear_labels_and_semantics() -> None:
    assert status_to_label("PRICE_INVALID") == "PRICE INVALID"
    assert status_to_semantic_color("ACTIONABLE_BUY") == "success"
    assert status_to_semantic_color("PRE_GATE_FAIL") == "error"

