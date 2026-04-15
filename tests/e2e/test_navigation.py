"""
Navigationstests: Alle Seiten sind erreichbar, keine crasht beim ersten Aufruf.

Geprüfte Seiten:
- Overview (Startseite / Dashboard)
- Methodik (immer verfügbar, kein DB-Zugriff)
- Explorer (erfordert MySQL – bei fehlendem DB graceful degradieren)
- Detailansicht (erfordert MySQL)
- Admin (erfordert MySQL)

Marker: @pytest.mark.navigation
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import (
    _wait_for_streamlit_ready,
    navigate_to_page,
    wait_for_no_streamlit_error,
    ACTION_TIMEOUT,
)


# ─────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────────────────

def _get_visible_nav_links(page: Page) -> list[str]:
    """Gibt die Titel aller sichtbaren Nav-Links zurück."""
    links = page.locator('[data-testid="stSidebarNav"] a, nav a').all()
    if not links:
        # Fallback: Streamlit navigation links via role
        links = page.get_by_role("link").all()
    return [lnk.inner_text().strip() for lnk in links if lnk.is_visible()]


def _page_has_heading(page: Page, text: str) -> bool:
    """Prüft ob eine Überschrift mit dem Text sichtbar ist."""
    try:
        page.get_by_role("heading", name=text).wait_for(state="visible", timeout=5000)
        return True
    except Exception:
        return False


def _page_shows_warning_not_crash(page: Page) -> None:
    """
    Unterscheidet zwischen einem erwarteten DB-Warning und einem echten Crash.

    Eine Warnung (st.warning) ist akzeptabel bei fehlender DB.
    Eine Exception-Box (stException) ist ein echter Fehler.
    """
    wait_for_no_streamlit_error(page)


# ─────────────────────────────────────────────────────────────────────────────
# Navigationstests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.navigation
def test_overview_page_loads(mercator_page: Page) -> None:
    """
    Die Startseite (Overview) lädt ohne Exception.

    Bei fehlendem MySQL erscheint eine Warnung – das ist kein Testfehler.
    """
    # Wir sind bereits auf der Startseite (default page)
    _page_shows_warning_not_crash(mercator_page)

    # Entweder "Overview" als Titel oder ein anderes sinnvolles Heading
    h1 = mercator_page.locator("h1").first
    expect(h1).to_be_visible()
    assert len(h1.inner_text().strip()) > 0


@pytest.mark.navigation
def test_methodology_page_loads(mercator_page: Page) -> None:
    """
    Die Methodik-Seite lädt immer – sie hat keine DB-Abhängigkeiten.
    """
    navigate_to_page(mercator_page, "Methodik")
    _page_shows_warning_not_crash(mercator_page)

    # Seite hat einen H1
    expect(mercator_page.locator("h1").first).to_be_visible()
    # Fachlicher Inhalt muss sichtbar sein
    expect(mercator_page.get_by_text("Architektur", exact=False).first).to_be_visible()


@pytest.mark.navigation
def test_methodology_page_content(mercator_page: Page) -> None:
    """
    Methodik-Seite zeigt erwartete Abschnitte: MongoDB, MySQL, Gate-Prüfung.
    """
    navigate_to_page(mercator_page, "Methodik")

    for expected_text in ["MongoDB", "MySQL", "Gate"]:
        expect(mercator_page.get_by_text(expected_text, exact=False).first).to_be_visible(
            timeout=ACTION_TIMEOUT
        )


@pytest.mark.navigation
def test_explorer_page_accessible(mercator_page: Page) -> None:
    """
    Die Explorer-Seite ist erreichbar.

    Bei fehlendem MySQL zeigt sie eine Warnung statt zu crashen.
    """
    # Explorer erscheint nur im Nav wenn MySQL verfügbar ist
    explorer_link = mercator_page.get_by_role("link", name="Explorer", exact=False)

    if not explorer_link.is_visible():
        pytest.skip("Explorer-Seite im Navigationsmenü nicht sichtbar (MySQL nicht verfügbar)")

    explorer_link.click()
    _wait_for_streamlit_ready(mercator_page)
    _page_shows_warning_not_crash(mercator_page)


@pytest.mark.navigation
def test_detail_page_accessible(mercator_page: Page) -> None:
    """
    Die Detailansicht ist erreichbar.

    Bei fehlendem MySQL zeigt sie eine Warnung statt zu crashen.
    """
    detail_link = mercator_page.get_by_role("link", name="Detailansicht", exact=False)

    if not detail_link.is_visible():
        pytest.skip("Detailansicht im Navigationsmenü nicht sichtbar (MySQL nicht verfügbar)")

    detail_link.click()
    _wait_for_streamlit_ready(mercator_page)
    _page_shows_warning_not_crash(mercator_page)


@pytest.mark.navigation
def test_admin_page_accessible(mercator_page: Page) -> None:
    """
    Die Admin-Seite ist erreichbar.

    Bei fehlendem MySQL zeigt sie eine Fehlermeldung (st.error) – kein Python-Crash.
    """
    admin_link = mercator_page.get_by_role("link", name="Admin", exact=False)
    expect(admin_link).to_be_visible()

    admin_link.click()
    _wait_for_streamlit_ready(mercator_page)

    # Admin benötigt MySQL – bei fehlendem DB st.error, kein stException
    exception_box = mercator_page.locator('[data-testid="stException"]')
    assert exception_box.count() == 0, (
        f"Admin-Seite zeigt Python-Exception statt kontrollierter Fehlermeldung:\n"
        f"{exception_box.first.inner_text() if exception_box.count() > 0 else ''}"
    )


@pytest.mark.navigation
def test_navigation_returns_to_overview(mercator_page: Page) -> None:
    """
    Von Methodik zurück zu Overview navigieren funktioniert.
    """
    navigate_to_page(mercator_page, "Methodik")
    _page_shows_warning_not_crash(mercator_page)

    navigate_to_page(mercator_page, "Overview")
    _page_shows_warning_not_crash(mercator_page)

    # Overview hat "Overview" als Titel (oder Fallback bei kein MySQL)
    h1 = mercator_page.locator("h1").first
    expect(h1).to_be_visible()


@pytest.mark.navigation
def test_all_nav_links_visible(mercator_page: Page) -> None:
    """
    Alle erwarteten Navigationspunkte sind mindestens sichtbar.

    Overview und Methodik sind immer vorhanden.
    Explorer/Detailansicht/Admin erscheinen je nach DB-Status.
    """
    sidebar = mercator_page.locator('[data-testid="stSidebar"]')

    # Diese beiden Seiten sind immer verfügbar
    for always_visible in ["Overview", "Methodik"]:
        expect(
            sidebar.get_by_role("link", name=always_visible, exact=False)
        ).to_be_visible(timeout=ACTION_TIMEOUT)

    # Admin ist immer registriert (auch bei kein MySQL)
    expect(
        sidebar.get_by_role("link", name="Admin", exact=False)
    ).to_be_visible(timeout=ACTION_TIMEOUT)

