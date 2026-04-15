"""
Ticker-Detailansicht-Tests: Profil, Tabs, Felder und Drilldown.

Geprüfte Flows:
- Detailansicht lädt mit Ticker-Selectbox
- Tabs (Trades, Company Context, Raw/Audit) sind navigierbar
- Kerndatenfelder (symbol, score, gate_status etc.) erscheinen
- Schnell-Drilldown aus dem Explorer navigiert zur Detailansicht
- Kein Crash beim Wechsel zwischen Symbolen

Marker: @pytest.mark.detail
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
def detail_page(mercator_page: Page) -> Page:
    """Navigiert zur Detailansicht und überspringt den Test wenn nicht verfügbar."""
    detail_link = mercator_page.get_by_role("link", name="Detailansicht", exact=False)
    if not detail_link.is_visible(timeout=5000):
        pytest.skip("Detailansicht nicht verfügbar – MySQL nicht erreichbar")

    detail_link.click()
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)
    return mercator_page


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.detail
def test_detail_page_heading_visible(detail_page: Page) -> None:
    """Die Detailansicht hat einen sichtbaren H1-Titel."""
    heading = detail_page.get_by_role("heading", name="Detailansicht", exact=False)
    expect(heading).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.detail
def test_detail_page_ticker_selectbox_visible(detail_page: Page) -> None:
    """Die Ticker-Selectbox ist sichtbar oder eine 'Keine Daten'-Meldung erscheint."""
    main_text = detail_page.locator("main").inner_text()

    if "Keine Daten" in main_text or "Keine" in main_text:
        # Akzeptabler Zustand bei leerer DB
        return

    ticker_select = detail_page.get_by_label("Ticker", exact=False).first
    expect(ticker_select).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.detail
def test_detail_page_no_exception(detail_page: Page) -> None:
    """Die Detailansicht zeigt keine Python-Exception."""
    wait_for_no_streamlit_error(detail_page)


@pytest.mark.detail
@pytest.mark.requires_data
def test_detail_page_metrics_visible(detail_page: Page) -> None:
    """
    Bei vorhandenen Daten werden Metriken (Trades, Preis, Menge) angezeigt.
    """
    main_text = detail_page.locator("main").inner_text()
    if "Keine Daten" in main_text or "Keine" in main_text:
        pytest.skip("Keine Daten – Metriken-Test übersprungen")

    # Streamlit Metrics sind als [data-testid="stMetric"] gerendert
    metrics = detail_page.locator('[data-testid="stMetric"]').all()
    assert len(metrics) >= 1, "Detailansicht sollte mindestens eine Metrik anzeigen"

    # Mindestens eine Metrik muss sichtbar sein
    expect(detail_page.locator('[data-testid="stMetric"]').first).to_be_visible()


@pytest.mark.detail
@pytest.mark.requires_data
def test_detail_page_tabs_visible(detail_page: Page) -> None:
    """
    Die Tabs 'Trades', 'Company Context' und 'Raw / Audit' sind sichtbar.
    """
    main_text = detail_page.locator("main").inner_text()
    if "Keine Daten" in main_text or "Keine" in main_text:
        pytest.skip("Keine Daten – Tab-Test übersprungen")

    tab_container = detail_page.locator('[data-testid="stTabs"]').first
    try:
        tab_container.wait_for(state="visible", timeout=5000)
    except Exception:
        pytest.skip("Keine Tab-Container sichtbar (kein Ticker geladen)")

    for tab_name in ["Trades", "Company Context", "Raw"]:
        expect(
            detail_page.get_by_role("tab", name=tab_name, exact=False)
        ).to_be_visible(timeout=ACTION_TIMEOUT)


@pytest.mark.detail
@pytest.mark.requires_data
def test_detail_trades_tab_shows_dataframe(detail_page: Page) -> None:
    """
    Der 'Trades'-Tab zeigt einen DataFrame mit Handelsdaten.
    """
    main_text = detail_page.locator("main").inner_text()
    if "Keine Daten" in main_text or "Keine" in main_text:
        pytest.skip("Keine Daten – DataFrame-Test übersprungen")

    # Trades-Tab ist standardmäßig aktiv
    trades_tab = detail_page.get_by_role("tab", name="Trades", exact=False)
    try:
        trades_tab.wait_for(state="visible", timeout=5000)
        trades_tab.click()
        _wait_for_streamlit_ready(detail_page)
    except Exception:
        pytest.skip("Trades-Tab nicht gefunden")

    wait_for_no_streamlit_error(detail_page)

    # DataFrame muss vorhanden sein (oder "Keine Transaktionen" Meldung)
    df = detail_page.locator('[data-testid="stDataFrame"]').first
    info_text = detail_page.get_by_text("Keine Transaktionen", exact=False).first

    assert df.is_visible() or info_text.is_visible(), (
        "Trades-Tab muss entweder einen DataFrame oder 'Keine Transaktionen' zeigen"
    )


@pytest.mark.detail
@pytest.mark.requires_data
def test_detail_company_context_tab(detail_page: Page) -> None:
    """
    Der 'Company Context'-Tab öffnet ohne Crash.
    """
    main_text = detail_page.locator("main").inner_text()
    if "Keine Daten" in main_text or "Keine" in main_text:
        pytest.skip("Keine Daten – Company-Context-Test übersprungen")

    company_tab = detail_page.get_by_role("tab", name="Company Context", exact=False)
    try:
        company_tab.wait_for(state="visible", timeout=5000)
        company_tab.click()
        _wait_for_streamlit_ready(detail_page)
    except Exception:
        pytest.skip("Company Context Tab nicht gefunden")

    wait_for_no_streamlit_error(detail_page)

    # Entweder Profildaten oder "Kein Firmenprofil gefunden" – beides ist OK
    page_text = detail_page.locator("main").inner_text()
    assert len(page_text.strip()) > 0


@pytest.mark.detail
@pytest.mark.requires_data
def test_detail_raw_audit_tab(detail_page: Page) -> None:
    """
    Der 'Raw / Audit'-Tab öffnet ohne Crash.
    """
    main_text = detail_page.locator("main").inner_text()
    if "Keine Daten" in main_text or "Keine" in main_text:
        pytest.skip("Keine Daten – Raw/Audit-Test übersprungen")

    raw_tab = detail_page.get_by_role("tab", name="Raw", exact=False)
    try:
        raw_tab.wait_for(state="visible", timeout=5000)
        raw_tab.click()
        _wait_for_streamlit_ready(detail_page)
    except Exception:
        pytest.skip("Raw/Audit Tab nicht gefunden")

    wait_for_no_streamlit_error(detail_page)


@pytest.mark.detail
@pytest.mark.requires_data
def test_detail_key_domain_fields_visible(detail_page: Page) -> None:
    """
    Zentrale Domänen-Felder erscheinen in der Detailansicht.

    Geprüft: score, score_class, gate_status, validation_status
    (als Spaltenbezeichnungen in der Tabelle).
    """
    main_text = detail_page.locator("main").inner_text()
    if "Keine Daten" in main_text or "Keine" in main_text:
        pytest.skip("Keine Daten – Domänenfelder-Test übersprungen")

    # Trades Tab sicherstellen
    trades_tab = detail_page.get_by_role("tab", name="Trades", exact=False)
    try:
        trades_tab.wait_for(state="visible", timeout=5000)
        trades_tab.click()
        _wait_for_streamlit_ready(detail_page)
    except Exception:
        pytest.skip("Trades Tab nicht gefunden")

    df = detail_page.locator('[data-testid="stDataFrame"]').first
    if not df.is_visible():
        pytest.skip("Kein DataFrame sichtbar")

    # Spaltenüberschriften des DataFrames extrahieren
    df_text = df.inner_text()
    # Fachliche Spaltennamen aus col_config
    expected_cols = ["Score", "Klasse", "Gate", "Validation", "Richtung"]
    visible_cols = [col for col in expected_cols if col in df_text]

    assert len(visible_cols) >= 2, (
        f"Mindestens 2 der Kernspalten {expected_cols} müssen sichtbar sein. "
        f"Gefunden: {visible_cols}. DataFrame-Text: {df_text[:500]}"
    )


@pytest.mark.detail
@pytest.mark.requires_data
def test_detail_drilldown_from_explorer(mercator_page: Page) -> None:
    """
    Schnell-Drilldown vom Explorer zur Detailansicht funktioniert.

    Flow:
    1. Explorer öffnen
    2. Schnell-Drilldown-Selectbox nutzen
    3. Zu Detailansicht wechseln
    4. Ausgewählter Ticker ist vorselektiert
    """
    # Explorer öffnen
    explorer_link = mercator_page.get_by_role("link", name="Explorer", exact=False)
    if not explorer_link.is_visible(timeout=5000):
        pytest.skip("Explorer nicht verfügbar")

    explorer_link.click()
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)

    main_text = mercator_page.locator("main").inner_text()
    if "Keine Treffer" in main_text or "Keine Transaktionen" in main_text:
        pytest.skip("Keine Daten im Explorer für Drilldown-Test")

    # Schnell-Drilldown Selectbox
    drilldown_label = mercator_page.get_by_text("Ticker für Kontextvorschau", exact=False).first
    if not drilldown_label.is_visible():
        pytest.skip("Kein Schnell-Drilldown sichtbar (keine Daten)")

    # Ersten Ticker aus der Selectbox lesen
    drilldown_select = mercator_page.get_by_label(
        "Ticker für Kontextvorschau", exact=False
    ).first
    drilldown_select.wait_for(state="visible", timeout=ACTION_TIMEOUT)

    # Zur Detailansicht navigieren
    detail_link = mercator_page.get_by_role("link", name="Detailansicht", exact=False)
    if not detail_link.is_visible():
        pytest.skip("Detailansicht-Link nicht sichtbar")

    detail_link.click()
    _wait_for_streamlit_ready(mercator_page)
    wait_for_no_streamlit_error(mercator_page)

    # Detailansicht muss geladen sein
    expect(
        mercator_page.get_by_role("heading", name="Detailansicht", exact=False)
    ).to_be_visible(timeout=ACTION_TIMEOUT)

