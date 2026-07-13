"""E2E smoke coverage for the watchlist-to-stock-detail workflow."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import ACTION_TIMEOUT, navigate_to_page, wait_for_no_streamlit_error


@pytest.mark.navigation
def test_stock_detail_shows_all_analysis_sections_and_text_statuses(mercator_page: Page) -> None:
    navigate_to_page(mercator_page, "Watchlist")
    mercator_page.get_by_label("Symbol für Detailanalyse").fill("AAPL")
    mercator_page.get_by_role("button", name="Analyse öffnen", exact=True).click()
    wait_for_no_streamlit_error(mercator_page)

    expect(mercator_page.get_by_role("heading", name="Aktienanalyse: AAPL", exact=False)).to_be_visible(
        timeout=ACTION_TIMEOUT
    )
    for section in [
        "Unternehmensprofil",
        "Kursübersicht",
        "Features",
        "Prognosen",
        "Preference Score",
        "Datenqualität",
    ]:
        expect(mercator_page.get_by_role("heading", name=section, exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)
    expect(mercator_page.get_by_text("fehlt", exact=False).first).to_be_visible(timeout=ACTION_TIMEOUT)
