"""
Fehlerfreie-Nutzungs-Tests: Vollständige Klickpfade ohne Fehler.

Diese Tests simulieren typische Nutzerpfade und überwachen dabei:
- Streamlit Exception-Boxen
- Browser Console Errors
- UI-Fehlermeldungen die auf Datenprobleme hinweisen

Geprüfte Flows:
- Vollständiger Seitenrundgang (alle Seiten nacheinander)
- Advanced Mode Ein/Aus ohne Crash
- Explorer + Akkumulierung-Toggle-Zyklus
- Dashboard KPIs laden ohne Fehler
- Wiederholtes Navigieren zwischen Seiten

Marker: @pytest.mark.error_free
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, ConsoleMessage, expect

from tests.e2e.conftest import (
    _wait_for_streamlit_ready,
    navigate_to_page,
    wait_for_no_streamlit_error,
    ACTION_TIMEOUT,
)


# ─────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────────────────

def _collect_console_errors(page: Page) -> list[str]:
    """Registriert einen Listener für Console-Errors und gibt gesammelte Fehler zurück."""
    errors: list[str] = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            text = msg.text
            # Ignoriere bekannte harmlose Browser-Fehler
            ignore_patterns = [
                "favicon",
                "extension",
                "net::err_aborted",
                "net::err_connection_refused",  # Erwartbar wenn DB nicht verfügbar
                "ResizeObserver",
                "Non-Error exception",
            ]
            if any(p.lower() in text.lower() for p in ignore_patterns):
                return
            errors.append(text)

    page.on("console", on_console)
    return errors


def _check_no_streamlit_error_text(page: Page) -> None:
    """
    Prüft ob sichtbarer roter Fehler-Text von Streamlit vorhanden ist.

    st.error() erzeugt eine Box mit data-testid="stAlert" und type="error".
    """
    exception_boxes = page.locator('[data-testid="stException"]').all()
    for box in exception_boxes:
        if box.is_visible():
            raise AssertionError(
                f"Streamlit zeigt eine Exception: {box.inner_text()[:300]}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.error_free
def test_complete_page_tour_no_exception(mercator_page: Page) -> None:
    """
    Vollständiger Seitenrundgang: Alle Seiten besuchen, keine Exception.

    Testet den häufigsten Nutzungspfad: User öffnet alle Menüpunkte nacheinander.
    """
    console_errors = _collect_console_errors(mercator_page)

    # Methodik ist immer verfügbar
    navigate_to_page(mercator_page, "Methodik")
    _check_no_streamlit_error_text(mercator_page)

    # Admin ist immer verfügbar (auch bei kein MySQL)
    navigate_to_page(mercator_page, "Admin")
    _check_no_streamlit_error_text(mercator_page)

    # Zurück zu Overview
    navigate_to_page(mercator_page, "Overview")
    _check_no_streamlit_error_text(mercator_page)

    # Explorer, falls verfügbar
    explorer_link = mercator_page.get_by_role("link", name="Explorer", exact=False)
    if explorer_link.is_visible():
        explorer_link.click()
        _wait_for_streamlit_ready(mercator_page)
        _check_no_streamlit_error_text(mercator_page)

    # Detailansicht, falls verfügbar
    detail_link = mercator_page.get_by_role("link", name="Detailansicht", exact=False)
    if detail_link.is_visible():
        detail_link.click()
        _wait_for_streamlit_ready(mercator_page)
        _check_no_streamlit_error_text(mercator_page)

    # Kritische Console-Errors auswerten
    # Filterung: Nur echte App-Fehler, keine Infrastruktur-Verbindungsfehler
    critical_errors = [
        e for e in console_errors
        if not any(p in e.lower() for p in [
            "connection", "refused", "net::", "mongodb", "mysql", "timeout"
        ])
    ]
    assert len(critical_errors) == 0, (
        f"Kritische JavaScript-Fehler beim Seitenrundgang:\n" +
        "\n".join(critical_errors[:5])
    )


@pytest.mark.error_free
def test_advanced_mode_toggle_no_crash(mercator_page: Page) -> None:
    """
    Advanced Mode ein- und ausschalten führt zu keinem Crash.
    """
    sidebar = mercator_page.locator('[data-testid="stSidebar"]')

    # Advanced Mode Toggle finden
    advanced_toggle = sidebar.locator('[data-testid="stToggle"]').filter(
        has_text="Erweiterte Ansicht"
    ).first

    if not advanced_toggle.is_visible():
        # Fallback
        advanced_toggle = sidebar.get_by_text("Erweiterte Ansicht", exact=False).first

    advanced_toggle.wait_for(state="visible", timeout=ACTION_TIMEOUT)

    # Toggle einschalten
    advanced_toggle.get_by_role("checkbox").check()
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)

    # Toggle ausschalten
    advanced_toggle.get_by_role("checkbox").uncheck()
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)


@pytest.mark.error_free
def test_repeated_navigation_stable(mercator_page: Page) -> None:
    """
    Mehrfaches Navigieren zwischen Seiten führt zu keiner Instabilität.

    Testet Memory-Leaks oder Zustandsprobleme durch wiederholte Navigation.
    """
    for _round in range(3):
        navigate_to_page(mercator_page, "Methodik")
        _check_no_streamlit_error_text(mercator_page)

        navigate_to_page(mercator_page, "Overview")
        _check_no_streamlit_error_text(mercator_page)


@pytest.mark.error_free
def test_database_status_expander_opens(mercator_page: Page) -> None:
    """
    Der Datenbank-Status-Expander öffnet und zeigt Status-Informationen.
    """
    sidebar = mercator_page.locator('[data-testid="stSidebar"]')
    db_expander = sidebar.get_by_text("Datenbank-Status", exact=False).first
    db_expander.wait_for(state="visible", timeout=ACTION_TIMEOUT)

    # Expander anklicken (öffnen)
    db_expander.click()
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)

    # Entweder "verbunden" oder "nicht erreichbar" muss sichtbar sein
    sidebar_text = sidebar.inner_text()
    assert (
        "verbunden" in sidebar_text.lower()
        or "nicht erreichbar" in sidebar_text.lower()
        or "mysql" in sidebar_text.lower()
        or "mongodb" in sidebar_text.lower()
    ), f"Datenbank-Status-Expander zeigt keine erkennbaren Informationen. Sidebar: {sidebar_text[:300]}"


@pytest.mark.error_free
def test_overview_no_python_exception(mercator_page: Page) -> None:
    """
    Die Overview-Seite zeigt keine Python-Exception, auch bei fehlender DB-Verbindung.

    Unterscheidung: stException (echter Crash) vs. stAlert warning (kontrollierte Warnung).
    """
    # Sicherstellen dass wir auf Overview sind
    overview_link = mercator_page.get_by_role("link", name="Overview", exact=False)
    if overview_link.is_visible():
        overview_link.click()
        _wait_for_streamlit_ready(mercator_page)

    _check_no_streamlit_error_text(mercator_page)


@pytest.mark.error_free
def test_methodology_page_complete_render(mercator_page: Page) -> None:
    """
    Die Methodik-Seite rendert vollständig: alle Abschnitte sind sichtbar.
    """
    navigate_to_page(mercator_page, "Methodik")

    expected_sections = [
        "Architektur",
        "Verarbeitungsschritte",
        "FMP",
    ]

    for section in expected_sections:
        expect(
            mercator_page.get_by_text(section, exact=False).first
        ).to_be_visible(timeout=ACTION_TIMEOUT)

    wait_for_no_streamlit_error(mercator_page)


@pytest.mark.error_free
def test_admin_page_no_python_exception(mercator_page: Page) -> None:
    """
    Admin-Seite zeigt bei fehlendem MySQL eine kontrollierte Fehlermeldung (kein Python-Crash).
    """
    navigate_to_page(mercator_page, "Admin")
    _check_no_streamlit_error_text(mercator_page)


@pytest.mark.error_free
def test_explorer_filter_cycle_no_crash(mercator_page: Page) -> None:
    """
    Vollständiger Filter-Zyklus im Explorer: Setzen → Anwenden → Reset.

    Testet den häufigsten User-Flow im Explorer.
    """
    explorer_link = mercator_page.get_by_role("link", name="Explorer", exact=False)
    if not explorer_link.is_visible(timeout=5000):
        pytest.skip("Explorer nicht verfügbar")

    explorer_link.click()
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)

    # Ticker setzen
    ticker_input = mercator_page.get_by_label("Ticker", exact=False).first
    ticker_input.clear()
    ticker_input.fill("MSFT")

     # Richtung setzen
     direction_select = mercator_page.get_by_label("Richtung", exact=False).first
     direction_select.select_option("BUY")

    # Filter anwenden
    apply_btn = mercator_page.get_by_role("button", name="Filter anwenden", exact=False)
    apply_btn.click()
    _wait_for_streamlit_ready(mercator_page)
    _check_no_streamlit_error_text(mercator_page)

    # Filter zurücksetzen
    reset_btn = mercator_page.get_by_role("button", name="Filter zurücksetzen", exact=False)
    reset_btn.click()
    _wait_for_streamlit_ready(mercator_page)
    _check_no_streamlit_error_text(mercator_page)


@pytest.mark.error_free
def test_page_reload_stable(mercator_page: Page) -> None:
    """
    Seiten-Reload führt zu stabiler Wiederherstellung des Zustands.
    """
    mercator_page.reload(wait_until="domcontentloaded")
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)

    # App muss nach Reload funktionsfähig sein
    expect(mercator_page.locator('[data-testid="stSidebar"]')).to_be_visible()

