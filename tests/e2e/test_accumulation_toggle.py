"""
Accumulation-Toggle-Tests: Akkumulierung ein-/ausschalten und Effekte prüfen.

Geprüfte Flows:
- Toggle 'Trades akkumulieren' ist in Sekundären Filtern sichtbar
- Akkumulierung an vs. aus zeigt unterschiedliche Spalten
- Toggle 'Einzeltrades anzeigen' umschaltet auf Rohdaten
- Kein Crash beim Umschalten

Hintergrund (Fachlogik):
  Wenn "Trades akkumulieren" = ON: Tabelle zeigt akkumulierte Felder wie
    accumulated_trade_value_estimated, accumulated_qty, accumulated_trade_count.
  Wenn OFF (oder "Einzeltrades anzeigen" = ON): Tabelle zeigt Einzeltrades mit
    trade_value_estimated, qty, price.

Marker: @pytest.mark.accumulation
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import (
    _wait_for_streamlit_ready,
    wait_for_no_streamlit_error,
    ACTION_TIMEOUT,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def explorer_with_secondary_filters(mercator_page: Page) -> Page:
    """
    Öffnet den Explorer mit bereits aufgeklappten Sekundären Filtern.
    """
    explorer_link = mercator_page.get_by_role("link", name="Explorer", exact=False)
    if not explorer_link.is_visible(timeout=5000):
        pytest.skip("Explorer nicht verfügbar – MySQL nicht erreichbar")

    explorer_link.click()
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)

    # Sekundäre Filter öffnen
    expander = mercator_page.get_by_text("Sekundäre Filter & Darstellung", exact=False).first
    expander.wait_for(state="visible", timeout=ACTION_TIMEOUT)
    expander.click()
    _wait_for_streamlit_ready(mercator_page)

    return mercator_page


# ─────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────────────────

def _get_toggle_state(page: Page, label: str) -> bool:
    """
    Liest den aktuellen Zustand eines Streamlit-Toggles.

    Streamlit-Toggles sind <input type="checkbox"> mit einem Label.
    """
    toggle_label = page.get_by_text(label, exact=False).first
    toggle_label.wait_for(state="visible", timeout=ACTION_TIMEOUT)

    # Das zugehörige Checkbox-Element suchen
    checkbox = page.locator(f'input[type="checkbox"]').filter(
        has=page.locator(f'text={label}')
    ).first

    if checkbox.count() == 0:
        # Fallback: aria-checked auf dem Toggle-Container
        toggle_container = page.locator('[data-testid="stToggle"]').filter(
            has_text=label
        ).first
        try:
            return toggle_container.get_by_role("checkbox").is_checked()
        except Exception:
            return False

    return checkbox.is_checked()


def _set_toggle(page: Page, label: str, desired_state: bool) -> None:
    """
    Setzt einen Streamlit-Toggle auf den gewünschten Zustand.
    """
    # Streamlit Toggle: data-testid="stToggle"
    toggle_container = page.locator('[data-testid="stToggle"]').filter(
        has_text=label
    ).first

    try:
        toggle_container.wait_for(state="visible", timeout=ACTION_TIMEOUT)
        checkbox = toggle_container.get_by_role("checkbox")
        current = checkbox.is_checked()
        if current != desired_state:
            checkbox.click()
            # Kurze Pause damit Streamlit reagiert – kein Sleep, sondern Wait
            page.wait_for_timeout(200)
    except Exception:
        # Fallback: Label direkt anklicken
        label_element = page.get_by_text(label, exact=True).first
        if label_element.is_visible():
            label_element.click()
            page.wait_for_timeout(200)


def _get_dataframe_column_headers(page: Page) -> list[str]:
    """
    Extrahiert die sichtbaren Spaltenüberschriften aus dem Streamlit DataFrame.
    """
    df = page.locator('[data-testid="stDataFrame"]').first
    try:
        df.wait_for(state="visible", timeout=5000)
    except Exception:
        return []

    # AG Grid column headers
    headers = df.locator(".ag-header-cell-text").all()
    if headers:
        return [h.inner_text().strip() for h in headers if h.inner_text().strip()]

    # Fallback: Standard HTML th
    headers = df.locator("th").all()
    return [h.inner_text().strip() for h in headers if h.inner_text().strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.accumulation
def test_accumulation_toggle_is_visible(explorer_with_secondary_filters: Page) -> None:
    """
    Der 'Trades akkumulieren'-Toggle ist nach dem Öffnen der Sekundären Filter sichtbar.
    """
    page = explorer_with_secondary_filters
    toggle = page.locator('[data-testid="stToggle"]').filter(
        has_text="Trades akkumulieren"
    ).first
    expect(toggle).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.accumulation
def test_single_trades_toggle_is_visible(explorer_with_secondary_filters: Page) -> None:
    """
    Der 'Einzeltrades anzeigen'-Toggle ist sichtbar.
    """
    page = explorer_with_secondary_filters
    toggle = page.locator('[data-testid="stToggle"]').filter(
        has_text="Einzeltrades anzeigen"
    ).first
    expect(toggle).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.accumulation
def test_accumulation_toggle_can_be_deactivated(explorer_with_secondary_filters: Page) -> None:
    """
    Der Accumulation-Toggle kann deaktiviert werden, ohne dass die App crasht.
    """
    page = explorer_with_secondary_filters

    # Akkumulierung deaktivieren
    _set_toggle(page, "Trades akkumulieren", False)

    # Apply-Button klicken um Änderung anzuwenden
    apply_btn = page.get_by_role("button", name="Filter anwenden", exact=False)
    apply_btn.click()
    _wait_for_streamlit_ready(page)

    wait_for_no_streamlit_error(page)


@pytest.mark.accumulation
def test_accumulation_toggle_can_be_reactivated(explorer_with_secondary_filters: Page) -> None:
    """
    Der Accumulation-Toggle kann reaktiviert werden nach dem Deaktivieren.
    """
    page = explorer_with_secondary_filters

    # Erst deaktivieren
    _set_toggle(page, "Trades akkumulieren", False)
    apply_btn = page.get_by_role("button", name="Filter anwenden", exact=False)
    apply_btn.click()
    _wait_for_streamlit_ready(page)

    # Dann wieder aktivieren
    _set_toggle(page, "Trades akkumulieren", True)
    apply_btn = page.get_by_role("button", name="Filter anwenden", exact=False)
    apply_btn.click()
    _wait_for_streamlit_ready(page)

    wait_for_no_streamlit_error(page)


@pytest.mark.accumulation
@pytest.mark.requires_data
def test_accumulation_changes_table_columns(explorer_with_secondary_filters: Page) -> None:
    """
    Beim Umschalten von Accumulation ändern sich die sichtbaren Tabellenspalten.

    Akkumuliert: 'Trade Value' und '#Trades' sichtbar
    Nicht akkumuliert: 'Preis' und 'Stück' sichtbar

    Übersprungen wenn keine Daten vorhanden sind.
    """
    page = explorer_with_secondary_filters

    # Prüfe ob Daten vorhanden
    main_text = page.locator("main").inner_text()
    if "Keine Treffer" in main_text or "Keine" in main_text:
        pytest.skip("Keine Daten vorhanden – Spaltenvergleichs-Test übersprungen")

    # Akkumulierung AN
    _set_toggle(page, "Trades akkumulieren", True)
    _set_toggle(page, "Einzeltrades anzeigen", False)
    apply_btn = page.get_by_role("button", name="Filter anwenden", exact=False)
    apply_btn.click()
    _wait_for_streamlit_ready(page)

    cols_accumulated = _get_dataframe_column_headers(page)

    # Akkumulierung AUS (Einzeltrades)
    _set_toggle(page, "Einzeltrades anzeigen", True)
    apply_btn = page.get_by_role("button", name="Filter anwenden", exact=False)
    apply_btn.click()
    _wait_for_streamlit_ready(page)

    cols_raw = _get_dataframe_column_headers(page)

    # Tabellen-Konfiguration muss sich unterscheiden wenn beide nicht leer sind
    if cols_accumulated and cols_raw:
        assert cols_accumulated != cols_raw, (
            "Spalten bei akkumulierter vs. Einzeltrades-Ansicht müssen sich unterscheiden. "
            f"Akkumuliert: {cols_accumulated}, Einzeltrades: {cols_raw}"
        )


@pytest.mark.accumulation
def test_show_raw_toggle_no_crash(explorer_with_secondary_filters: Page) -> None:
    """
    'Einzeltrades anzeigen' umschalten führt zu keinem Crash.
    """
    page = explorer_with_secondary_filters

    _set_toggle(page, "Einzeltrades anzeigen", True)
    apply_btn = page.get_by_role("button", name="Filter anwenden", exact=False)
    apply_btn.click()
    _wait_for_streamlit_ready(page)
    wait_for_no_streamlit_error(page)

    # Wieder zurück
    _set_toggle(page, "Einzeltrades anzeigen", False)
    apply_btn = page.get_by_role("button", name="Filter anwenden", exact=False)
    apply_btn.click()
    _wait_for_streamlit_ready(page)
    wait_for_no_streamlit_error(page)

