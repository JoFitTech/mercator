# Mercator – E2E-Browser-Tests (Playwright)

Diese Dokumentation beschreibt die End-to-End-Testinfrastruktur für die
Mercator Streamlit-App. Die Tests öffnen einen echten Browser (Chromium)
und klicken die App so durch, wie es ein Nutzer tun würde.

---

## Schnellstart

```powershell
# 1. Test-Abhängigkeiten installieren
python -m pip install -r requirements-dev.txt

# 2. Playwright-Browser herunterladen (einmalig)
python -m playwright install chromium

# 3. Streamlit-App starten (in separatem Terminal)
streamlit run streamlit_app.py

# 4. E2E-Tests ausführen
pytest tests/e2e/ -v
```

Optional über das Projektskript:

```powershell
.\mercator.ps1 e2e-install
.\mercator.ps1 e2e-smoke
```

Optional mit Auto-Start der App durch die Test-Fixtures:

```powershell
$env:MERCATOR_E2E_AUTOSTART = "true"
pytest tests/e2e/test_navigation.py -v
```

---

## Voraussetzungen

| Voraussetzung | Beschreibung |
|---|---|
| Python 3.11+ | Im Projekt vorhandene Version |
| Playwright | `pip install playwright` (optional zusätzlich `pytest-playwright`) |
| Chromium | `python -m playwright install chromium` |
| Streamlit App | Muss auf `http://localhost:8501` laufen |

---

## Teststruktur

```
tests/
  e2e/
    conftest.py                     # Fixtures, Hilfsfunktionen, Playwright-Konfiguration
    test_smoke.py                   # Schnelle Grundprüfung: App startet
    test_navigation.py              # Navigation zwischen allen Seiten
    test_explorer_filters.py        # Explorer-Filterformular und Filter-Flows
    test_accumulation_toggle.py     # Akkumulierungs-Toggle ein/aus
    test_trade_detail.py            # Ticker-Detailansicht, Tabs, Felder
    test_error_free_interactions.py # Vollständige Klickpfade ohne Ausnahmen
    screenshots/                    # Automatische Screenshots bei Fehlern (gitignored)
    traces/                         # Playwright-Traces bei Fehlern (gitignored)
```

---

## Testmarker

| Marker | Beschreibung |
|---|---|
| `smoke` | Schnellste Tests – App ist erreichbar, kein Crash |
| `navigation` | Alle Seiten sind navigierbar |
| `explorer` | Explorer-Filterformular |
| `accumulation` | Akkumulierungs-Toggle |
| `detail` | Ticker-Detailansicht |
| `error_free` | Vollständige Nutzerpfade ohne JS/Python-Fehler |
| `requires_data` | Test benötigt echte DB-Daten (übersprungen bei leerer DB) |

---

## Nützliche Befehle

```powershell
# Nur Smoke-Tests (schnellstes Feedback, ~15s)
pytest tests/e2e/ -m smoke -v

# Navigationsvalidierung (Header/Sidebar + Sequenzen)
pytest tests/e2e/test_navigation.py -v

# Tests ohne Datenbankabhängigkeit
pytest tests/e2e/ -m "not requires_data" -v

# Einzelne Testdatei
pytest tests/e2e/test_smoke.py -v

# Mit sichtbarem Browser (Debugging)
$env:MERCATOR_E2E_HEADLESS = "false"
pytest tests/e2e/ -v

# Langsam ausführen (Debugging, 500ms zwischen Aktionen)
$env:MERCATOR_E2E_SLOW_MO = "500"
$env:MERCATOR_E2E_HEADLESS = "false"
pytest tests/e2e/test_explorer_filters.py -v

# Navigationstest gegen andere URL (z.B. Staging)
$env:MERCATOR_E2E_BASE_URL = "http://staging-server:8501"
pytest tests/e2e/ -m smoke -v

# Alternative Konfiguration über .env.e2e
Copy-Item .env.e2e.example .env.e2e
pytest tests/e2e/ -m smoke -v
```

---

## Konfiguration (Umgebungsvariablen)

| Variable | Standard | Beschreibung |
|---|---|---|
| `MERCATOR_E2E_BASE_URL` | `http://localhost:8501` | URL der laufenden Streamlit-App |
| `MERCATOR_E2E_HEADLESS` | `true` | Browser im Headless-Modus |
| `MERCATOR_E2E_SLOW_MO` | `0` | Verzögerung zwischen Aktionen (ms) |
| `MERCATOR_E2E_PAGE_LOAD_TIMEOUT_MS` | `30000` | Timeout für das initiale Laden |
| `MERCATOR_E2E_ACTION_TIMEOUT_MS` | `15000` | Timeout für UI-Aktionen |
| `MERCATOR_E2E_STREAMLIT_READY_TIMEOUT_MS` | `20000` | Warten auf Streamlit-Bereitschaft |
| `MERCATOR_E2E_AUTOSTART` | `false` | Startet Streamlit automatisch (nur localhost/127.0.0.1) |
| `MERCATOR_E2E_APP_START_TIMEOUT_SECONDS` | `90` | Timeout für den automatischen App-Start |
| `MERCATOR_E2E_CHROMIUM_EXECUTABLE` | _leer_ | Optionaler Pfad zu System-Chromium/Chrome, falls Playwright-Browser nicht installierbar sind |

`tests/e2e/conftest.py` lädt zusätzlich automatisch eine optionale Datei `.env.e2e`,
falls sie im Projekt-Root existiert.

---

## Verhalten bei fehlender Datenbankverbindung

Die Tests sind so konzipiert, dass sie auch **ohne MySQL oder MongoDB** laufen:

- **Smoke-Tests**: Laufen immer (testen nur App-Erreichbarkeit und Grundstruktur)
- **Navigationstests**: Laufen größtenteils (Explorer/Detailansicht werden übersprungen wenn kein MySQL)
- **Explorer/Detail/Accumulation**: Werden automatisch übersprungen (`pytest.skip`) wenn MySQL nicht verfügbar
- **`requires_data`-Tests**: Werden übersprungen wenn die DB leer ist

Das ist **absichtliches Verhalten** – die App degradiert kontrolliert bei fehlendem MySQL.

---

## Artefakte bei Fehlern

Bei einem fehlgeschlagenen Test werden automatisch gespeichert:

- **Screenshot**: `tests/e2e/screenshots/<testname>_failure.png`
- **Trace**: `tests/e2e/traces/<testname>_failure.zip`

Traces können mit dem Playwright-Trace-Viewer geöffnet werden:

```powershell
python -m playwright show-trace tests/e2e/traces/test_name_failure.zip
```

---

## Geprüfte Nutzerflows

| Flow | Test-Datei | Beschreibung |
|---|---|---|
| App-Start | `test_smoke.py` | Seite lädt, kein Crash, Titel korrekt |
| Alle Seiten navigieren | `test_navigation.py` | Kein Crash auf allen Seiten |
| Explorer öffnen | `test_explorer_filters.py` | Formular sichtbar, Filter-Buttons vorhanden |
| Ticker-Filter setzen | `test_explorer_filters.py` | Eingabe → Anwenden → Ergebnis ändert sich |
| Filter zurücksetzen | `test_explorer_filters.py` | Zustand wird sauber zurückgesetzt |
| Akkumulierung an/aus | `test_accumulation_toggle.py` | Toggle ändert sichtbare Spalten |
| Detailansicht öffnen | `test_trade_detail.py` | Tabs und Metriken sichtbar |
| Domänenfelder sichtbar | `test_trade_detail.py` | Score, Gate-Status, Validation sichtbar |
| Seitenrundgang | `test_error_free_interactions.py` | Alle Seiten ohne JS/Python-Fehler |
| Advanced Mode Toggle | `test_error_free_interactions.py` | Kein Crash beim Umschalten |
| Reload stabil | `test_error_free_interactions.py` | Nach Reload App funktionsfähig |

---

## Erkannte Fehlerklassen

Diese Tests erkennen Fehler, die **statische Prüfung und Unit-Tests nicht finden**:

| Fehlerklasse | Erkannt durch |
|---|---|
| Python-Exception beim Seitenaufruf | Alle Tests via `stException`-Check |
| Fehlendes UI-Element / Label | Locator-Assertions mit `expect()` |
| Filter-Apply löst Fehler aus | Explorer-Filter-Tests |
| Toggle-Umschaltung crasht | Accumulation-Tests |
| Navigation crasht Seite | Navigationstests |
| JavaScript-Fehler im Browser | Console-Error-Listener in `test_error_free_interactions.py` |
| Streamlit-Session-State-Fehler | Wiederholte Navigation und Reload-Tests |
| Leere Daten ohne Meldung | `requires_data`-Tests mit Inhaltsprüfung |
| Seite hängt (Timeout) | Playwright-Timeouts lösen AssertionError aus |

---

## CI-Integration (optional)

```yaml
# Beispiel: GitHub Actions
- name: Install dev dependencies
  run: pip install -r requirements-dev.txt

- name: Install Playwright browsers
  run: python -m playwright install chromium

- name: Start Streamlit app
  run: streamlit run streamlit_app.py &
  env:
    MERCATOR_UI_TEST_MODE: "true"

- name: Wait for app
  run: sleep 10

- name: Run E2E tests
  run: pytest tests/e2e/ -m "not requires_data" -v
  env:
    MERCATOR_E2E_BASE_URL: http://localhost:8501
    MERCATOR_E2E_HEADLESS: "true"
```

---

## Offene Risiken

| Risiko | Beschreibung | Maßnahme |
|---|---|---|
| Streamlit-Updates | Playwright-Selektoren können sich bei Streamlit-Major-Updates ändern | Selektoren regelmäßig prüfen |
| AG-Grid-Spalten | DataFrame-Spalten via AG-Grid sind schwer selektierbar | Fallback auf `inner_text()` implementiert |
| Timing-Probleme | Streamlit rerendert nach Interaktion asynchron | `_wait_for_streamlit_ready()` als robuste Wait-Strategie |
| Echte DB benötigt | `requires_data`-Tests brauchen gefüllte DB | Klare Skip-Logik, kein stiller Fehler |
| Windows-spezifisch | `playwright install` kann unter Windows langsam sein | Einmalig, Chromium ~150MB |
