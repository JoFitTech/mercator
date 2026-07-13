"""
Watchlist-E2E-Smoke-Test.

Der Test setzt voraus, dass die Streamlit-App fuer E2E laeuft oder per
MERCATOR_E2E_AUTOSTART=true gestartet wird.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import ACTION_TIMEOUT, navigate_to_page, wait_for_no_streamlit_error


@pytest.mark.navigation
def test_watchlist_page_shows_status_text_columns(mercator_page: Page) -> None:
    navigate_to_page(mercator_page, "Watchlist")
    wait_for_no_streamlit_error(mercator_page)

    expect(mercator_page.get_by_role("heading", name="Watchlist", exact=False)).to_be_visible(
        timeout=ACTION_TIMEOUT
    )
    expect(mercator_page.get_by_text("Profil", exact=False).first).to_be_visible(timeout=ACTION_TIMEOUT)
    expect(mercator_page.get_by_text("Kurs", exact=False).first).to_be_visible(timeout=ACTION_TIMEOUT)
    expect(mercator_page.get_by_text("Finanz", exact=False).first).to_be_visible(timeout=ACTION_TIMEOUT)
    expect(mercator_page.get_by_text("Preference", exact=False).first).to_be_visible(timeout=ACTION_TIMEOUT)
