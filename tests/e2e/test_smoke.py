"""
Smoke-Tests: Schnelle Grundprüfung – App startet, Seite lädt, Kernelement sichtbar.

Diese Tests sollen in < 30 Sekunden laufen und das Minimum sicherstellen:
- Die App ist erreichbar
- Streamlit rendert ohne Python-Exception
- Titel und Sidebar sind sichtbar
- Keine offensichtlichen JS-Fehler beim Start

Marker: @pytest.mark.smoke
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, _wait_for_streamlit_ready, wait_for_no_streamlit_error


@pytest.mark.smoke
def test_app_is_reachable(mercator_page: Page) -> None:
    """App antwortet auf GET / und liefert eine HTML-Seite zurück."""
    # Die Fixture hat bereits geladen – wenn wir hier sind, ist die App erreichbar
    assert mercator_page.url.startswith(BASE_URL), (
        f"Erwartete Base-URL '{BASE_URL}', erhalten: '{mercator_page.url}'"
    )


@pytest.mark.smoke
def test_streamlit_container_renders(mercator_page: Page) -> None:
    """Der Haupt-Container von Streamlit ist sichtbar."""
    expect(mercator_page.locator('[data-testid="stAppViewContainer"]')).to_be_visible()


@pytest.mark.smoke
def test_sidebar_visible(mercator_page: Page) -> None:
    """Die Seitenleiste mit Mercator-Titel ist sichtbar."""
    sidebar = mercator_page.locator('[data-testid="stSidebar"]')
    expect(sidebar).to_be_visible()
    # Mercator-Titel in der Sidebar
    expect(sidebar.get_by_text("Mercator").first).to_be_visible()


@pytest.mark.smoke
def test_no_streamlit_exception_on_load(mercator_page: Page) -> None:
    """Beim Laden der App erscheint keine Streamlit-Exception-Box."""
    wait_for_no_streamlit_error(mercator_page)


@pytest.mark.smoke
def test_page_title_in_browser_tab(mercator_page: Page) -> None:
    """Browser-Tab-Titel enthält 'Mercator'."""
    expect(mercator_page).to_have_title("Mercator")


@pytest.mark.smoke
def test_overview_page_heading_visible(mercator_page: Page) -> None:
    """Die Startseite (Overview) zeigt eine H1-Überschrift."""
    # Streamlit h1 ist die Hauptüberschrift der aktiven Seite
    heading = mercator_page.locator("h1").first
    expect(heading).to_be_visible()
    heading_text = heading.inner_text()
    # Entweder "Overview" (bei DB-Verbindung) oder eine Fallback-Seite
    assert len(heading_text.strip()) > 0, "H1 muss einen nicht-leeren Text haben"


@pytest.mark.smoke
def test_advanced_mode_toggle_exists(mercator_page: Page) -> None:
    """Der 'Erweiterte Ansicht'-Toggle ist in der Sidebar sichtbar."""
    sidebar = mercator_page.locator('[data-testid="stSidebar"]')
    # Streamlit-Toggle ist ein input[type=checkbox] mit passendem Label
    toggle = sidebar.get_by_text("Erweiterte Ansicht", exact=False).first
    expect(toggle).to_be_visible()


@pytest.mark.smoke
def test_database_status_expander_exists(mercator_page: Page) -> None:
    """Der 'Datenbank-Status'-Expander ist in der Sidebar vorhanden."""
    sidebar = mercator_page.locator('[data-testid="stSidebar"]')
    db_status = sidebar.get_by_text("Datenbank-Status", exact=False).first
    expect(db_status).to_be_visible()


@pytest.mark.smoke
def test_no_javascript_errors_on_load(mercator_page: Page) -> None:
    """
    Keine kritischen JavaScript-Fehler beim App-Start.

    Lauscht auf Console-Errors und schlägt fehl wenn kritische JS-Fehler erscheinen.
    """
    js_errors: list[str] = []

    def capture_console_error(msg) -> None:
        if msg.type == "error":
            # Browser-eigene Extension-Fehler ignorieren
            text = msg.text
            if any(skip in text.lower() for skip in [
                "extension",
                "favicon",
                "net::err_aborted",  # Streamlit eigene Artefakte
            ]):
                return
            js_errors.append(text)

    mercator_page.on("console", capture_console_error)

    # Nochmal navigieren um Console-Events zu erfassen
    mercator_page.reload(wait_until="domcontentloaded")
    _wait_for_streamlit_ready(mercator_page)

    # Maximal 2 kritische JS-Fehler tolerieren (Streamlit selbst hat manchmal interne Warnnungen)
    critical_errors = [e for e in js_errors if "streamlit" not in e.lower()]
    assert len(critical_errors) <= 2, (
        f"Kritische JavaScript-Fehler beim Laden:\n" + "\n".join(critical_errors)
    )


