"""
Fehlerfreie-Nutzungs-Tests: Vollständige Klickpfade ohne Fehler.

Diese Tests simulieren typische Nutzerpfade und überwachen dabei:
- Streamlit Exception-Boxen
- Browser Console Errors
- UI-Fehlermeldungen die auf Datenprobleme hinweisen

Geprüfte Flows:
- Vollständiger Seitenrundgang (aktuelle Haupt- und Verwaltungsseiten)
- Sidebar-Verwaltung öffnet ohne Crash
- Trades-Filter-Zyklus ohne Python-Exception
- Dashboard KPIs laden ohne Fehler
- Wiederholtes Navigieren zwischen Seiten

Marker: @pytest.mark.error_free
"""

from __future__ import annotations

import pytest
from playwright.sync_api import ConsoleMessage, Page, expect

from tests.e2e.conftest import (
    _wait_for_streamlit_ready,
    navigate_to_page,
    wait_for_no_streamlit_error,
    ACTION_TIMEOUT,
)


def _collect_console_errors(page: Page) -> list[str]:
    """Registriert einen Listener für Console-Errors und gibt gesammelte Fehler zurück."""
    errors: list[str] = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            text = msg.text
            ignore_patterns = [
                "favicon",
                "extension",
                "net::err_aborted",
                "net::err_connection_refused",
                "ResizeObserver",
                "Non-Error exception",
            ]
            if any(p.lower() in text.lower() for p in ignore_patterns):
                return
            errors.append(text)

    page.on("console", on_console)
    return errors



def _check_no_streamlit_error_text(page: Page) -> None:
    """Prüft, ob eine Streamlit-Exception sichtbar ist."""
    exception_boxes = page.locator('[data-testid="stException"]').all()
    for box in exception_boxes:
        if box.is_visible():
            raise AssertionError(
                f"Streamlit zeigt eine Exception: {box.inner_text()[:300]}"
            )


@pytest.mark.error_free
def test_complete_page_tour_no_exception(mercator_page: Page) -> None:
    """Besucht die aktuellen Kernseiten nacheinander und erwartet keine Python-Exception."""
    console_errors = _collect_console_errors(mercator_page)

    for page_name in ["Dashboard", "Trades", "Unternehmen", "Methodik", "Einstellungen", "Admin"]:
        navigate_to_page(mercator_page, page_name)
        _check_no_streamlit_error_text(mercator_page)

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
def test_sidebar_management_expander_no_crash(mercator_page: Page) -> None:
    """Das Öffnen der neuen Verwaltung/Hilfe-Sektion in der Sidebar führt zu keinem Crash."""
    sidebar = mercator_page.locator('[data-testid="stSidebar"]')
    management_expander = sidebar.get_by_text("Verwaltung & Hilfe", exact=False).first
    management_expander.wait_for(state="visible", timeout=ACTION_TIMEOUT)

    management_expander.click()
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)

    sidebar_text = sidebar.inner_text()
    assert any(label in sidebar_text for label in ["Einstellungen", "Admin", "Methodik"])


@pytest.mark.error_free
def test_repeated_navigation_stable(mercator_page: Page) -> None:
    """Mehrfaches Navigieren zwischen Seiten führt zu keiner Instabilität."""
    for _round in range(3):
        navigate_to_page(mercator_page, "Methodik")
        _check_no_streamlit_error_text(mercator_page)

        navigate_to_page(mercator_page, "Dashboard")
        _check_no_streamlit_error_text(mercator_page)


@pytest.mark.error_free
def test_database_status_expander_opens(mercator_page: Page) -> None:
    """Der System-Status-Expander öffnet und zeigt Status-Informationen."""
    sidebar = mercator_page.locator('[data-testid="stSidebar"]')
    db_expander = sidebar.get_by_text("System-Status", exact=False).first
    db_expander.wait_for(state="visible", timeout=ACTION_TIMEOUT)

    db_expander.click()
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)

    sidebar_text = sidebar.inner_text()
    assert (
        "verbunden" in sidebar_text.lower()
        or "nicht erreichbar" in sidebar_text.lower()
        or "mysql" in sidebar_text.lower()
        or "mongodb" in sidebar_text.lower()
        or "online" in sidebar_text.lower()
        or "offline" in sidebar_text.lower()
    ), f"System-Status-Expander zeigt keine erkennbaren Informationen. Sidebar: {sidebar_text[:300]}"


@pytest.mark.error_free
def test_dashboard_no_python_exception(mercator_page: Page) -> None:
    """Die Dashboard-Seite zeigt keine Python-Exception, auch bei fehlender DB-Verbindung."""
    navigate_to_page(mercator_page, "Dashboard")
    _check_no_streamlit_error_text(mercator_page)


@pytest.mark.error_free
def test_methodology_page_complete_render(mercator_page: Page) -> None:
    """Die Methodik-Seite rendert vollständig: alle Abschnitte sind sichtbar."""
    navigate_to_page(mercator_page, "Methodik")

    expected_sections = [
        "Übersicht",
        "Speicherstrategie",
        "Scoring-Modell",
    ]

    for section in expected_sections:
        expect(
            mercator_page.get_by_text(section, exact=False).first
        ).to_be_visible(timeout=ACTION_TIMEOUT)

    wait_for_no_streamlit_error(mercator_page)


@pytest.mark.error_free
def test_admin_page_no_python_exception(mercator_page: Page) -> None:
    """Admin-Seite zeigt keinen Python-Crash."""
    navigate_to_page(mercator_page, "Admin")
    _check_no_streamlit_error_text(mercator_page)


@pytest.mark.error_free
def test_trades_filter_cycle_no_crash(mercator_page: Page) -> None:
    """Vollständiger Filter-Zyklus in Trades: Setzen → Anwenden → Reset."""
    navigate_to_page(mercator_page, "Trades")
    wait_for_no_streamlit_error(mercator_page)

    symbol_input = mercator_page.get_by_label("Symbol", exact=False).first
    try:
        symbol_input.wait_for(state="visible", timeout=2000)
    except Exception:
        filter_expander = mercator_page.get_by_text("Filter und Suche", exact=False).first
        if filter_expander.count() == 0:
            pytest.skip("Trades-Filter im aktuellen Modus nicht verfügbar (degraded/offline).")
        filter_expander.click()
        _wait_for_streamlit_ready(mercator_page)
        symbol_input = mercator_page.get_by_label("Symbol", exact=False).first
        try:
            symbol_input.wait_for(state="visible", timeout=ACTION_TIMEOUT)
        except Exception:
            pytest.skip("Trades-Filter im aktuellen Modus nicht interaktiv verfügbar.")

    symbol_input.fill("")
    symbol_input.fill("MSFT")

    direction_select = mercator_page.get_by_label("Richtung", exact=False).first
    direction_select.select_option("BUY")

    apply_btn = mercator_page.get_by_role("button", name="Filter anwenden", exact=False)
    apply_btn.click()
    _wait_for_streamlit_ready(mercator_page)
    _check_no_streamlit_error_text(mercator_page)

    reset_btn = mercator_page.get_by_role("button", name="Filter zurücksetzen", exact=False)
    reset_btn.click()
    _wait_for_streamlit_ready(mercator_page)
    _check_no_streamlit_error_text(mercator_page)


@pytest.mark.error_free
def test_page_reload_stable(mercator_page: Page) -> None:
    """Seiten-Reload führt zu stabiler Wiederherstellung des Zustands."""
    mercator_page.reload(wait_until="domcontentloaded")
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)
    expect(mercator_page.locator('[data-testid="stSidebar"]')).to_be_visible()

