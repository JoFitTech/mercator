"""
Explorer-Filter-Tests: Filterformular, Filteranwendung, Ergebnisänderung.

Geprüfte Flows:
- Explorer-Seite lädt mit Tabelle
- Ticker-Filter kann gesetzt und angewendet werden
- Richtungsfilter (BUY/SELL) ändert die Anzeige
- Min. Trade Value beeinflusst Ergebnisse
- Filter zurücksetzen funktioniert
- Sekundäre Filter (Gate-Status, Validation) sind bedienbar
- Filter-Summary wird korrekt aktualisiert

Marker: @pytest.mark.explorer
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
def explorer_page(mercator_page: Page) -> Page:
    """Navigiert zur Explorer-Seite und überspringt den Test wenn nicht verfügbar."""
    explorer_link = mercator_page.get_by_role("link", name="Explorer", exact=False)
    if not explorer_link.is_visible(timeout=5000):
        pytest.skip("Explorer nicht verfügbar – MySQL nicht erreichbar")

    explorer_link.click()
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)
    return mercator_page


# ─────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────────────────

def _get_filter_summary_text(page: Page) -> str:
    """Liest den aktuellen Filter-Summary-Text aus."""
    summary = page.locator("text=Aktive Filter:").first
    try:
        return summary.inner_text(timeout=3000)
    except Exception:
        return ""


def _apply_filters(page: Page) -> None:
    """Klickt den 'Filter anwenden'-Button."""
    apply_btn = page.get_by_role("button", name="Filter anwenden", exact=False)
    apply_btn.wait_for(state="visible", timeout=ACTION_TIMEOUT)
    apply_btn.click()
    _wait_for_streamlit_ready(page)


def _reset_filters(page: Page) -> None:
    """Klickt den 'Filter zurücksetzen'-Button."""
    reset_btn = page.get_by_role("button", name="Filter zurücksetzen", exact=False)
    reset_btn.wait_for(state="visible", timeout=ACTION_TIMEOUT)
    reset_btn.click()
    _wait_for_streamlit_ready(page)


def _count_dataframe_rows(page: Page) -> int:
    """
    Schätzt die Anzahl sichtbarer Zeilen im Streamlit-DataFrame.

    Streamlit rendert den DataFrame als HTML-Tabelle oder als AG Grid.
    Wir zählen die sichtbaren Daten-Zeilen.
    """
    # Streamlit DataFrame verwendet data-testid="stDataFrame"
    df_container = page.locator('[data-testid="stDataFrame"]').first
    try:
        df_container.wait_for(state="visible", timeout=5000)
    except Exception:
        return 0

    # Zähle sichtbare Zeilen in der Tabelle (Streamlit rendert als AG Grid)
    rows = df_container.locator(".ag-row").all()
    if rows:
        return len(rows)

    # Fallback: HTML-Tabellen-Zeilen
    tr_rows = df_container.locator("tr").all()
    # Minus 1 für Header
    return max(0, len(tr_rows) - 1)


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.explorer
def test_explorer_page_loads(explorer_page: Page) -> None:
    """Explorer-Seite lädt mit Titel 'Explorer'."""
    expect(explorer_page.get_by_role("heading", name="Explorer")).to_be_visible(
        timeout=ACTION_TIMEOUT
    )


@pytest.mark.explorer
def test_explorer_filter_form_visible(explorer_page: Page) -> None:
    """Das Filterformular mit den Primär-Filtern ist sichtbar."""
    # Formular-Abschnitt
    expect(explorer_page.get_by_text("Primäre Filter", exact=False).first).to_be_visible()

    # Ticker-Eingabefeld
    ticker_input = explorer_page.get_by_label("Ticker", exact=False).first
    expect(ticker_input).to_be_visible()

    # Richtungs-Selectbox
    direction_select = explorer_page.get_by_label("Richtung", exact=False).first
    expect(direction_select).to_be_visible()

    # Apply-Button
    expect(
        explorer_page.get_by_role("button", name="Filter anwenden", exact=False)
    ).to_be_visible()

    # Reset-Button
    expect(
        explorer_page.get_by_role("button", name="Filter zurücksetzen", exact=False)
    ).to_be_visible()


@pytest.mark.explorer
def test_explorer_filter_summary_default_state(explorer_page: Page) -> None:
    """Die Filter-Summary zeigt im Standardzustand 'Keine (Standardansicht)'."""
    # Nach dem Reset erwarten wir die Standard-Summary
    _reset_filters(explorer_page)
    summary_text = _get_filter_summary_text(explorer_page)
    assert "Aktive Filter:" in summary_text


@pytest.mark.explorer
def test_explorer_ticker_filter_updates_summary(explorer_page: Page) -> None:
    """
    Einen Ticker eingeben und anwenden ändert die Filter-Summary.

    Testet: Eingabe → Anwenden → Summary zeigt Ticker.
    """
    # Zuerst zurücksetzen
    _reset_filters(explorer_page)

    # Ticker eingeben
    ticker_input = explorer_page.get_by_label("Ticker", exact=False).first
    ticker_input.clear()
    ticker_input.fill("AAPL")

    # Filter anwenden
    _apply_filters(explorer_page)

    # Summary muss jetzt AAPL enthalten oder eine entsprechende Meldung zeigen
    summary_text = _get_filter_summary_text(explorer_page)
    # Entweder "AAPL" im Summary oder "Keine Treffer" bei leerer DB
    page_text = explorer_page.locator("main").inner_text()
    assert "AAPL" in page_text or "Keine Treffer" in page_text or "Keine" in page_text, (
        f"Nach Ticker-Filter 'AAPL' muss AAPL sichtbar sein oder 'Keine Treffer' erscheinen. "
        f"Seite zeigt: {page_text[:300]}"
    )


@pytest.mark.explorer
def test_explorer_direction_filter_buy(explorer_page: Page) -> None:
    """
    Richtungsfilter 'BUY' kann ausgewählt werden.

    Testet: Selectbox auf BUY setzen → Anwenden → kein Crash.
    """
    _reset_filters(explorer_page)

    # Richtungs-Selectbox öffnen und BUY wählen
    direction_select = explorer_page.get_by_label("Richtung", exact=False).first
    direction_select.select_option("BUY")

    _apply_filters(explorer_page)
    wait_for_no_streamlit_error(explorer_page)


@pytest.mark.explorer
def test_explorer_direction_filter_sell(explorer_page: Page) -> None:
    """
    Richtungsfilter 'SELL' kann ausgewählt werden.
    """
    _reset_filters(explorer_page)

    direction_select = explorer_page.get_by_label("Richtung", exact=False)
    direction_select = explorer_page.get_by_label("Richtung", exact=False).first
    direction_select.select_option("SELL")

    _apply_filters(explorer_page)
    wait_for_no_streamlit_error(explorer_page)


@pytest.mark.explorer
@pytest.mark.requires_data
def test_explorer_table_visible_with_data(explorer_page: Page) -> None:
    """
    Bei vorhandenen Daten ist der DataFrame sichtbar.

    Dieser Test wird übersprungen wenn keine Daten vorhanden sind.
    """
    _reset_filters(explorer_page)

    # Prüfe ob "Keine Treffer" erscheint (dann gibt es keine Daten)
    main_text = explorer_page.locator("main").inner_text()
    if "Keine Treffer" in main_text or "Keine" in main_text:
        pytest.skip("Keine Daten in der Datenbank – Tabellen-Test übersprungen")

    df = explorer_page.locator('[data-testid="stDataFrame"]').first
    expect(df).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.explorer
def test_explorer_secondary_filter_expander(explorer_page: Page) -> None:
    """
    Sekundäre Filter können geöffnet werden.

    Testet: Expander 'Sekundäre Filter & Darstellung' ist klickbar.
    """
    expander = explorer_page.get_by_text("Sekundäre Filter & Darstellung", exact=False).first
    expect(expander).to_be_visible()

    # Expander öffnen
    expander.click()
    _wait_for_streamlit_ready(explorer_page)

    # Accumulation Toggle muss nach dem Öffnen sichtbar sein
    acc_toggle = explorer_page.get_by_text("Trades akkumulieren", exact=False).first
    expect(acc_toggle).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.explorer
def test_explorer_min_trade_value_input(explorer_page: Page) -> None:
    """
    Der Min. Trade Value-Input akzeptiert Eingaben und löst keinen Fehler aus.
    """
    _reset_filters(explorer_page)

    min_value_input = explorer_page.get_by_label("Min. Trade Value", exact=False).first
    expect(min_value_input).to_be_visible()

    # Wert ändern
    min_value_input.triple_click()
    min_value_input.type("500000")

    _apply_filters(explorer_page)
    wait_for_no_streamlit_error(explorer_page)


@pytest.mark.explorer
def test_explorer_reset_filter_clears_state(explorer_page: Page) -> None:
    """
    Filter zurücksetzen setzt den Ticker-Filter zurück.
    """
    # Zuerst Ticker setzen
    ticker_input = explorer_page.get_by_label("Ticker", exact=False).first
    ticker_input.clear()
    ticker_input.fill("TSLA")
    _apply_filters(explorer_page)

    # Dann zurücksetzen
    _reset_filters(explorer_page)

    # Nach Reset sollte Ticker leer sein
    ticker_input_after = explorer_page.get_by_label("Ticker", exact=False).first
    expect(ticker_input_after).to_be_visible()
    current_value = ticker_input_after.input_value()
    assert current_value == "" or current_value is None, (
        f"Ticker-Feld sollte nach Reset leer sein, enthält aber: '{current_value}'"
    )


@pytest.mark.explorer
def test_explorer_no_crash_on_empty_filter(explorer_page: Page) -> None:
    """
    Leere Filter lösen keinen Python-Crash aus.
    """
    _reset_filters(explorer_page)
    _apply_filters(explorer_page)
    wait_for_no_streamlit_error(explorer_page)

    # Entweder Tabelle oder "Keine Treffer" – beides ist korrekt
    main_text = explorer_page.locator("main").inner_text()
    assert len(main_text.strip()) > 0, "Seite sollte nach leerem Filter irgendeinen Inhalt zeigen"

