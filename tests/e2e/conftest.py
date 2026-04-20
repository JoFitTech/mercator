"""
Playwright E2E-Test-Fixtures für Mercator.

Konfiguration:
  - Base-URL: Umgebungsvariable MERCATOR_E2E_BASE_URL (Standard: http://localhost:8501)
  - Screenshots bei Fehlern: automatisch im Verzeichnis tests/e2e/screenshots/
  - Tracing: wird bei Fehlern als ZIP gespeichert (tests/e2e/traces/)
  - Headless-Modus: MERCATOR_E2E_HEADLESS=true (Standard: true)

Lokale Ausführung:
  1. Streamlit-App starten: streamlit run streamlit_app.py
  2. Tests starten: pytest tests/e2e/ -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - Fallback für Minimalumgebungen
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env.e2e", override=False)

# ─────────────────────────────────────────────────────────────────────────────
# Konfiguration aus Umgebungsvariablen
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL: str = os.getenv("MERCATOR_E2E_BASE_URL", "http://localhost:8501")
HEADLESS: bool = os.getenv("MERCATOR_E2E_HEADLESS", "true").lower() not in {"false", "0", "no"}
SLOW_MO: int = int(os.getenv("MERCATOR_E2E_SLOW_MO", "0"))

# Timeouts (ms)
PAGE_LOAD_TIMEOUT: int = int(os.getenv("MERCATOR_E2E_PAGE_LOAD_TIMEOUT_MS", "30000"))
ACTION_TIMEOUT: int = int(os.getenv("MERCATOR_E2E_ACTION_TIMEOUT_MS", "15000"))
STREAMLIT_READY_TIMEOUT: int = int(os.getenv("MERCATOR_E2E_STREAMLIT_READY_TIMEOUT_MS", "20000"))

# Artefakt-Verzeichnisse
ARTIFACT_DIR = Path(__file__).parent
SCREENSHOT_DIR = ARTIFACT_DIR / "screenshots"
TRACE_DIR = ARTIFACT_DIR / "traces"

SCREENSHOT_DIR.mkdir(exist_ok=True)
TRACE_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# pytest-Hooks: pytest.ini-Optionen
# ─────────────────────────────────────────────────────────────────────────────

def pytest_configure(config: pytest.Config) -> None:
    """Registriert eigene Marker."""
    config.addinivalue_line("markers", "smoke: Schnelle Smoke-Tests – App startet und lädt")
    config.addinivalue_line("markers", "navigation: Navigation zwischen Seiten")
    config.addinivalue_line("markers", "explorer: Explorer-Seite und Filter-Flows")
    config.addinivalue_line("markers", "accumulation: Accumulation-Toggle-Tests")
    config.addinivalue_line("markers", "detail: Ticker-Detailansicht-Tests")
    config.addinivalue_line("markers", "error_free: Fehlerfreiheits-Prüfungen")
    config.addinivalue_line("markers", "requires_data: Test benötigt echte Datenbankdaten")


# ─────────────────────────────────────────────────────────────────────────────
# Browser-Fixture (Session-Scope → ein Browser für alle Tests)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Erweitert die Standard-Playwright-Kontext-Argumente."""
    return {
        **browser_context_args,
        "base_url": BASE_URL,
        "viewport": {"width": 1400, "height": 900},
        "locale": "de-DE",
        "timezone_id": "Europe/Berlin",
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict) -> dict:
    """Setzt Browser-Launch-Optionen."""
    return {
        **browser_type_launch_args,
        "headless": HEADLESS,
        "slow_mo": SLOW_MO,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Kontext-Fixture mit Tracing
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def context(
    browser: Browser,
    browser_context_args: dict,
    request: pytest.FixtureRequest,
) -> BrowserContext:
    """Ersetzt das Standard-Kontext-Fixture und speichert Trace-Artefakte bei Fehlern."""
    ctx = browser.new_context(**browser_context_args)
    ctx.set_default_timeout(ACTION_TIMEOUT)
    ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
    yield ctx

    test_name = _sanitize_test_name(request.node.name)
    trace_path = TRACE_DIR / f"{test_name}_failure.zip"
    failed = _test_failed(request)
    try:
        if failed:
            ctx.tracing.stop(path=str(trace_path))
        else:
            ctx.tracing.stop()
    finally:
        ctx.close()


# ─────────────────────────────────────────────────────────────────────────────
# Haupt-Page-Fixture: Navigiert zur App, wartet auf Streamlit-Bereitschaft
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mercator_page(page: Page, request: pytest.FixtureRequest) -> Page:
    """
    Öffnet die Mercator-App und wartet bis Streamlit vollständig geladen ist.

    Liefert eine fertig geladene Page-Instanz zurück.
    Bei Fehlern werden Screenshot und Trace gespeichert.
    """
    page.set_default_timeout(ACTION_TIMEOUT)

    try:
        page.goto("/", wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        _wait_for_streamlit_ready(page)
    except Exception as exc:
        _save_failure_artifacts(page, request, "setup")
        raise RuntimeError(f"Mercator-App konnte nicht geladen werden: {exc}") from exc

    yield page

    # Artefakte bei Testfehlern speichern
    if _test_failed(request):
        _save_failure_artifacts(page, request, "failure")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call):
    """Speichert Testergebnis auf dem Item für spätere Fixture-Auswertung."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# ─────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────────────────

def _wait_for_streamlit_ready(page: Page, timeout_ms: int = STREAMLIT_READY_TIMEOUT) -> None:
    """
    Wartet robust darauf, dass Streamlit vollständig geladen ist.

    Strategie:
    1. Warte auf das stAppViewContainer (Haupt-App-Container)
    2. Warte bis kein aktiver Spinner mehr sichtbar ist
    3. Stelle sicher, dass Seitenleiste existiert (Navigation geladen)
    """
    # Schritt 1: Haupt-Container muss erscheinen
    page.wait_for_selector(
        '[data-testid="stAppViewContainer"]',
        state="visible",
        timeout=timeout_ms,
    )

    # Schritt 2: Warte bis der Streamlit-Ladeindikator verschwindet
    # Streamlit zeigt einen "Running"-Status während der Initialisierung
    try:
        page.wait_for_selector(
            '[data-testid="stStatusWidget"]',
            state="detached",
            timeout=5000,
        )
    except Exception:
        # Falls kein Spinner vorhanden war – kein Problem
        pass

    # Schritt 3: Sidebar muss sichtbar sein (Navigation geladen)
    page.wait_for_selector(
        '[data-testid="stSidebar"]',
        state="visible",
        timeout=timeout_ms,
    )


def _save_failure_artifacts(page: Page, request: pytest.FixtureRequest, phase: str) -> None:
    """Speichert Screenshot und Trace bei Testfehlern."""
    test_name = _sanitize_test_name(request.node.name)

    # Screenshot
    screenshot_path = SCREENSHOT_DIR / f"{test_name}_{phase}.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:
        pass


def _sanitize_test_name(name: str) -> str:
    return name.replace("[", "_").replace("]", "_").replace("/", "_").replace("::", "_")


def _test_failed(request: pytest.FixtureRequest) -> bool:
    rep_setup = getattr(request.node, "rep_setup", None)
    rep_call = getattr(request.node, "rep_call", None)
    return bool((rep_setup and rep_setup.failed) or (rep_call and rep_call.failed))


_PAGE_ALIASES = {
    "Overview": "Dashboard",
    "Explorer": "Trades",
    "Detailansicht": "Trade-Detail",
}

_HEADER_PAGES = {"Dashboard", "Trades", "Unternehmen"}
_SIDEBAR_PAGES = {"Methodik", "Einstellungen", "Admin"}


def _resolve_page_alias(page_title: str) -> str:
    return _PAGE_ALIASES.get(page_title, page_title)


def _click_first_visible(locators: list) -> bool:
    for locator in locators:
        try:
            if locator.is_visible(timeout=1500):
                locator.click()
                return True
        except Exception:
            continue
    return False


def _expand_sidebar_management(page: Page) -> None:
    sidebar = page.locator('[data-testid="stSidebar"]')
    expander = sidebar.get_by_text("Verwaltung & Hilfe", exact=False).first
    expander.wait_for(state="visible", timeout=ACTION_TIMEOUT)
    expander.click()
    page.wait_for_timeout(150)


def navigate_to_page(page: Page, page_title: str) -> None:
    """
    Navigiert zu einer benannten Seite über die Streamlit-Navigation.

    Unterstützt die aktuelle Header-Button-Navigation sowie die Sidebar-Verwaltung.
    Wartet anschließend auf das Laden der Seite.
    """
    resolved_title = _resolve_page_alias(page_title)

    if resolved_title in _HEADER_PAGES:
        clicked = _click_first_visible([
            page.locator('[data-testid="stSegmentedControl"]').get_by_text(resolved_title, exact=False).first,
            page.get_by_role("radio", name=resolved_title, exact=False).first,
            page.get_by_role("button", name=resolved_title, exact=False).first,
            page.get_by_text(resolved_title, exact=False).first,
        ])
        if not clicked:
            raise AssertionError(f"Header-Navigation für '{resolved_title}' nicht gefunden.")
        _wait_for_streamlit_ready(page)
        return

    if resolved_title in _SIDEBAR_PAGES:
        _expand_sidebar_management(page)
        sidebar = page.locator('[data-testid="stSidebar"]')
        clicked = _click_first_visible([
            sidebar.get_by_role("button", name=resolved_title, exact=False).first,
            sidebar.get_by_text(resolved_title, exact=False).first,
        ])
        if not clicked:
            raise AssertionError(f"Sidebar-Navigation für '{resolved_title}' nicht gefunden.")
        _wait_for_streamlit_ready(page)
        return

    raise AssertionError(f"Navigation zu '{page_title}' wird von navigate_to_page nicht unterstützt.")


def wait_for_no_streamlit_error(page: Page) -> None:
    """
    Prüft, ob Streamlit eine Fehlermeldung anzeigt.

    Raises AssertionError wenn eine Fehlermeldung sichtbar ist.
    """
    # Streamlit Exception-Box
    error_box = page.locator('[data-testid="stException"]')
    if error_box.count() > 0:
        error_text = error_box.first.inner_text()
        raise AssertionError(f"Streamlit zeigt eine Fehlermeldung: {error_text}")


