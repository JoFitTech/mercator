"""E2E smoke coverage for transparent model evaluation."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import ACTION_TIMEOUT, navigate_to_page, wait_for_no_streamlit_error


@pytest.mark.navigation
def test_model_evaluation_shows_metric_definitions_and_freshness(mercator_page: Page) -> None:
    navigate_to_page(mercator_page, "Modellbewertung")
    wait_for_no_streamlit_error(mercator_page)

    expect(mercator_page.get_by_role("heading", name="Modellbewertung", exact=False)).to_be_visible(
        timeout=ACTION_TIMEOUT
    )
    expect(mercator_page.get_by_text("Metrikdefinitionen", exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)
    expect(mercator_page.get_by_text("Datenfrische", exact=False).first).to_be_visible(timeout=ACTION_TIMEOUT)
    for metric in ["Accuracy", "Precision", "Recall", "MAE"]:
        expect(mercator_page.get_by_text(metric, exact=True).first).to_be_visible(timeout=ACTION_TIMEOUT)
