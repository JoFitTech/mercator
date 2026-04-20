"""
Navigationstests für die aktuelle Mercator-UI.

Geprüfte Seiten:
- Dashboard (Startseite)
- Trades
- Unternehmen
- Methodik
- Einstellungen
- Admin

Marker: @pytest.mark.navigation
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import (
    navigate_to_page,
    wait_for_no_streamlit_error,
    ACTION_TIMEOUT,
)


def _page_shows_warning_not_crash(page: Page) -> None:
    """Erlaubt kontrollierte Warnungen, aber keine Python-Exception."""
    wait_for_no_streamlit_error(page)


@pytest.mark.navigation
def test_dashboard_page_loads(mercator_page: Page) -> None:
    """Die Startseite lädt ohne Python-Exception."""
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.locator("h1").first).to_be_visible()


@pytest.mark.navigation
def test_methodology_page_loads(mercator_page: Page) -> None:
    navigate_to_page(mercator_page, "Methodik")
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.get_by_role("heading", name="Methodik & Architektur", exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.navigation
def test_trades_page_accessible(mercator_page: Page) -> None:
    navigate_to_page(mercator_page, "Trades")
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.get_by_role("heading", name="Trades", exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.navigation
def test_companies_page_accessible(mercator_page: Page) -> None:
    navigate_to_page(mercator_page, "Unternehmen")
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.get_by_role("heading", name="Unternehmen", exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.navigation
def test_settings_page_accessible(mercator_page: Page) -> None:
    navigate_to_page(mercator_page, "Einstellungen")
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.get_by_role("heading", name="Einstellungen", exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.navigation
def test_admin_page_accessible(mercator_page: Page) -> None:
    navigate_to_page(mercator_page, "Admin")
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.get_by_role("heading", name="Admin", exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.navigation
def test_navigation_returns_to_dashboard(mercator_page: Page) -> None:
    navigate_to_page(mercator_page, "Methodik")
    _page_shows_warning_not_crash(mercator_page)

    navigate_to_page(mercator_page, "Dashboard")
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.locator("h1").first).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.navigation
def test_header_and_sidebar_navigation_controls_visible(mercator_page: Page) -> None:
    header = mercator_page.locator('[data-testid="stSegmentedControl"]').first
    expect(header).to_be_visible(timeout=ACTION_TIMEOUT)

    for primary_page in ["Dashboard", "Trades", "Unternehmen"]:
        expect(header.get_by_text(primary_page, exact=False).first).to_be_visible(timeout=ACTION_TIMEOUT)

    sidebar = mercator_page.locator('[data-testid="stSidebar"]')
    expect(sidebar.get_by_text("Verwaltung & Hilfe", exact=False).first).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.navigation
def test_header_sidebar_header_switch_stays_stable(mercator_page: Page) -> None:
    navigate_to_page(mercator_page, "Admin")
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.get_by_role("heading", name="Admin", exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)

    navigate_to_page(mercator_page, "Trades")
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.get_by_role("heading", name="Trades", exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)

    navigate_to_page(mercator_page, "Einstellungen")
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.get_by_role("heading", name="Einstellungen", exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.navigation
def test_sidebar_pages_remain_stable_without_header_reset(mercator_page: Page) -> None:
    for sidebar_page in ["Admin", "Einstellungen", "Methodik"]:
        navigate_to_page(mercator_page, sidebar_page)
        _page_shows_warning_not_crash(mercator_page)
        expect(mercator_page.get_by_role("heading", name=sidebar_page, exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.navigation
def test_methodik_dashboard_unternehmen_sequence(mercator_page: Page) -> None:
    navigate_to_page(mercator_page, "Methodik")
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.get_by_role("heading", name="Methodik", exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)

    navigate_to_page(mercator_page, "Dashboard")
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.locator("h1").first).to_be_visible(timeout=ACTION_TIMEOUT)

    navigate_to_page(mercator_page, "Unternehmen")
    _page_shows_warning_not_crash(mercator_page)
    expect(mercator_page.get_by_role("heading", name="Unternehmen", exact=False)).to_be_visible(timeout=ACTION_TIMEOUT)
