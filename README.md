# Mercator

## Kurzbeschreibung
Mercator ist eine interaktive Datenanwendung für das Modul **Datenbanken 2**. Die Anwendung verarbeitet öffentlich verfügbare Insider-Trade-Daten und stellt sie in einer Streamlit-Oberfläche analysierbar dar.

## Ziel der Anwendung
1. öffentliche Finanzdaten laden (FMP API)
2. Rohdaten in MongoDB speichern
3. bereinigte Daten in MySQL speichern
4. Ergebnisse interaktiv in Streamlit visualisieren
5. Methodik und Datenfluss für akademische Zwecke transparent machen

## Uni-Kontext und Scope
Mercator ist bewusst als akademisches MVP ausgelegt:
- Fokus auf nachvollziehbaren Datenfluss
- klare Trennung von Roh- und Zieldaten
- keine Produkt-/Enterprise-Nebenziele
- Alle Komponenten wurden konsequent auf den Projektnamen `mercator` umgestellt (Docker-Container, UI-Branding, Datenbanken). Altbestände (`finanzport-*`) werden automatisch bereinigt.

## Verwendete Technologien
- Python
- Streamlit
- Pandas
- MySQL (`mysql-connector-python`)
- MongoDB (`pymongo`)
- `python-dotenv`
- `requests`
- `pytest`

## Projektstruktur
- `streamlit_app.py` – Einstiegspunkt
- `src/config/` – App-, API- und DB-Konfiguration
- `src/models/` – Dataclasses (`InsiderTrade`, `Company`, `AnalysisResult`)
- `src/data_sources/` – FMP-Client (freigegebene Endpunkte)
- `src/preprocessing/` – Cleaning, Normalization, Deduplication, Gate-Evaluation
- `src/db/` – MongoDB-/MySQL-Clients und Repositories
- `src/services/` – Import-, Dashboard- und Analyse-Logik
- `src/ui/pages/` – Dashboard, Explorer, Ticker-Detail, Methodik
- `src/ui/components/` – Wiederverwendbare UI-Bausteine
- `src/utils/` – Hilfsfunktionen
- `tests/` – robuste Basistests
- `tests/e2e/` – Browserbasierte End-to-End-Tests mit Playwright

## Dokumentation
- [Methodik & Architektur](src/ui/pages/methodology_page.py) (UI-Seite)
- [Technisches Datenmodell](src/db/mysql_repository.py)
- [E2E Browser-Tests mit Playwright](README-E2E.md)
- [Steuerungsskripte-Übersicht](SKRIPTE.md) (mercator.ps1 / mercator.bat / mercator)
- [Quick Reference](QUICK_REF.md) (schnelle Befehlsübersicht)

## Datenfluss
1. `ImportService` lädt `Latest Insider Trading` von FMP (`page=0`, `limit=100`).
2. Rohobjekte werden normalisiert, typisiert und dedupliziert.
3. Rohdaten landen in MongoDB (`insider_trades_raw`).
4. Gate-Pass-Kandidaten lösen optionalen Profilabruf aus (`/profile-cik` primär, `/profile` als Fallback), inkl. TTL-Cache.
5. Bereinigte Trades und Profile werden in MySQL gespeichert.
6. `AccumulationService` aggregiert Trades in der UI-Schicht (Explorer, Ticker-Detail) nach fachlichen Regeln:
    - Gleiche Person (Reporting CIK/Name)
    - Gleiche Firma (Company CIK/Ticker)
    - Gleiche Richtung (Buy/Sell) und Wertpapierart
    - Zeitlicher Abstand maximal 1 Kalendertag
7. Streamlit-Seiten lesen über `AnalysisService` aus den Repositories.

## UI & Features
- **Dashboard**: Zentrale Kennzahlen, Sektoren-Verteilung, Volumen-Trends (Buy vs. Sell) und Zeitverläufe.
- **Explorer (Screener)**: Kompakte, eckige Tabellenansicht mit Fokus auf Scanbarkeit.
    - Akkumulations-Toggle: Zusammenfassung konsekutiver Trades einer Person.
    - Filter für Ticker, Insider, Richtung und Mindestwert.
    - **NEU**: Zeilenselektion für direkten Drilldown in die Detailansicht.
- **Ticker-Detailansicht (Deep Dive)**: 
    - Strukturierte Tabs für Übersicht, Firmenkontext und Rohdaten.
    - Detaillierte Auflistung von Akkumulationsgruppen und deren Einzeltrades.
    - Sichere Formatierung von Kennzahlen (Kompaktwerte wie 1.25M).

## Lokale Einrichtung
### Windows (Normale cmd.exe oder PowerShell – empfohlen)
Wenn du **nur testen/starten** willst, brauchst du lokal **kein Python**, solange Docker Desktop läuft.

```cmd
REM Im Windows Terminal (cmd.exe oder PowerShell)
git clone <this-repo-url> mercator
cd mercator
copy .env.example .env
mercator.bat start
mercator.bat open
```

oder in PowerShell:
```powershell
git clone <this-repo-url> mercator
cd mercator
Copy-Item .env.example .env -Force
.\mercator.ps1 start
.\mercator.ps1 open
```

### Windows + Git Bash / WSL
Falls du Git Bash oder WSL installiert hast:

```bash
git clone <this-repo-url> mercator
cd mercator
cp .env.example .env
chmod +x mercator
./mercator start
./mercator open
```

### macOS / Linux (Bash)
```bash
git clone <this-repo-url> mercator
cd mercator
cp .env.example .env
chmod +x mercator
./mercator start
./mercator open
```

Wichtig:
- **Windows Standard:** Verwende `mercator.bat start` oder `.\mercator.ps1 start`
- **Windows + Git Bash/WSL:** Verwende `./mercator start`
- **macOS/Linux:** Verwende `./mercator start`
- Wenn `python`, `pip` oder `streamlit` nicht gefunden werden, ist lokal noch kein Python installiert. Fuer den Docker-Start ist das aber **nicht noetig**.

### Lokale Python-Umgebung (nur wenn du ohne Docker entwickeln willst)
```powershell
cd mercator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Falls `py` ebenfalls nicht gefunden wird, installiere zuerst Python 3.11 fuer Windows.

### macOS / Linux (Bash)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run streamlit_app.py
```

## Umgebungsvariablen
Siehe `.env.example`.

Pflichtvariablen (MySQL-Mehrzielbetrieb):
- `MYSQL_ACTIVE_TARGET` (`local` oder `uni`)
- `MYSQL_AUTO_FALLBACK_TO_LOCAL` (`true`/`false`)
- `LOCAL_MYSQL_HOST`, `LOCAL_MYSQL_PORT`, `LOCAL_MYSQL_DATABASE`, `LOCAL_MYSQL_USER`, `LOCAL_MYSQL_PASSWORD`
- `UNI_MYSQL_HOST`, `UNI_MYSQL_PORT`, `UNI_MYSQL_DATABASE`, `UNI_MYSQL_USER`, `UNI_MYSQL_PASSWORD`
- `MONGO_URI`, `MONGO_DATABASE`
- `FMP_API_KEY`
- `APP_ENV`, `APP_TITLE`, `DATASET_PATH`

Kompatibilität:
- Bestehende `MYSQL_*` Variablen werden weiter als Fallback für das lokale Ziel unterstützt.

Optionale Import-/Gate-Parameter:
- `GATE_MIN_TRADE_VALUE` (Default `10000`)
- `GATE_REQUIRE_PURCHASE_EVENT` (`true`/`false`)
- `GATE_REQUIRE_COMMON_STOCK` (`true`/`false`)
- `PROFILE_GATE_FILTER_STATUSES` (CSV, z. B. `PASS` oder `PASS,PENDING`)


## In-App-Konfiguration (Advanced Mode)
Die Anwendung verfügt über einen **Advanced Mode** in der Sidebar, der zusätzliche Details und technische Informationen freischaltet:
- Erweiterte Tabellenspalten im Explorer.
- Detaillierte Unternehmensinformationen in der Ticker-Ansicht.
- Einblick in Gate-Regeln und Import-Details im Dashboard.
- Zusätzliche Analyse-Metriken.

Default-Modus: Reduziert, klar und auf die wesentlichen fachlichen Aussagen fokussiert.

## MySQL-Target-Switch (local/uni)
- Das aktive Ziel wird per `MYSQL_ACTIVE_TARGET` gewählt.
- In der Streamlit-Sidebar kann das Ziel pro Laufzeit zwischen `local` und `uni` umgeschaltet werden (`st.session_state`).
- Wenn `MYSQL_ACTIVE_TARGET=uni` gesetzt ist und die Uni-DB nicht erreichbar ist, kann optional auf `local` zurückgefallen werden (`MYSQL_AUTO_FALLBACK_TO_LOCAL=true`).
- Der Fallback ist technisch transparent: der Resolver liefert Hinweise, statt still zu verschleiern.
- Ohne Uni-WLAN funktioniert in der Regel nur `local`, sofern kein externer Zugriff auf die Uni-DB möglich ist.
- Im Docker-Stack zeigt `local` auf den Compose-Service `mysql`; bei nativem Start bleibt `local` typischerweise `localhost`.

## Kontrollierter MySQL-Sync
- Sync ist explizit und per Env steuerbar (`MYSQL_SYNC_ENABLED=true|false`).
- Default-Richtung im aktuellen Stand: `local -> uni`.
- Betroffene Tabellen: `companies` und `insider_trades`.
- Verfahren: SQL-basierte Upserts (`companies` über `company_key`, `insider_trades` über `dedupe_key`).
- Es gibt **keinen** automatischen Hintergrund-Sync beim App-Start.
- Der Sync wird nur über den Sidebar-Button ausgelöst, wenn `uni` erreichbar ist.

## Datenbank-Statusanzeigen in der UI
- MySQL- und MongoDB-Status werden getrennt angezeigt.
- Bei Uni-Ausfall mit erlaubtem Fallback wird der Wechsel auf `local` explizit ausgewiesen.
- Wenn nur MongoDB ausfällt, bleibt die App für MySQL-basierte Auswertungen nutzbar; Rohdatenspeicherung/Import ist dann eingeschränkt.

## Start der Anwendung
```bash
streamlit run streamlit_app.py
```

## Schnelleinstieg – Cheat Sheet

**Windows (cmd.exe oder PowerShell):**
```cmd
mercator.bat start       REM Startet alles
mercator.bat open        REM Öffnet im Browser
mercator.bat status      REM Zeigt Container
mercator.bat logs        REM Live-Logs der App
mercator.bat cleanup     REM Bereinigt alte Container
```

oder in PowerShell:
```powershell
.\mercator.ps1 start
.\mercator.ps1 open
.\mercator.ps1 status
.\mercator.ps1 logs
```

**Bash / WSL / Linux:**
```bash
./mercator start
./mercator open
./mercator status
./mercator logs
```

Oder ausführlich: Siehe [Steuerungsskripte-Übersicht](SKRIPTE.md).

## One-File Steuerung (Start/Stop/Restart)

### Für Windows Benutzer (Standard)
Nutze zentral `mercator.bat` oder `mercator.ps1`:

```cmd
mercator.bat start
mercator.bat status
mercator.bat logs
mercator.bat open
```

### Für macOS / Linux Benutzer
Nutze `mercator`:

```bash
./mercator start
./mercator status
./mercator logs
./mercator open
```

### Für Windows + Git Bash / WSL
Verwende entweder das Batch-Skript oder das Bash-Skript:

```bash
./mercator start              # Bash-Wrapper
# oder
../mercator.bat start         # Batch-Skript
```
- `start` - startet das Projekt (Uni-DB bevorzugt, sonst lokal)
- `stop` - stoppt den Stack
- `restart` - startet den Stack neu (inkl. Cleanup alter Container)
- `status` - zeigt Containerstatus
- `logs` - streamt Logs (default Service `app`)
- `init-db` - initialisiert das MySQL-Schema für **alle** Ziele (local + uni)
- `doctor` - führt einen detaillierten Schema-Check und Reparaturen durch
- `open` - oeffnet `http://localhost:8501`
- `cleanup` - entfernt verwaiste Container (Präfix `mercator-*` oder `finanzport-*`)
- `e2e-install` - installiert Dev-/Playwright-Abhängigkeiten und Chromium
- `e2e-smoke` - führt die schnellen Browser-Smoke-Tests gegen die laufende App aus
- `e2e` - führt die gesamte Playwright-E2E-Suite gegen die laufende App aus

Beispiele:

```powershell
.\mercator.ps1 status
.\mercator.ps1 restart
.\mercator.ps1 logs
.\mercator.ps1 logs -Service mongo
.\mercator.ps1 init-db
.\mercator.ps1 e2e-install
.\mercator.ps1 e2e-smoke
```

In der Dashboard-Seite kannst du unter **Gate- und Profil-Einstellungen** die Kriterien editieren
und persistent in MongoDB (`app_settings`) speichern. Ohne gespeicherte Werte gelten `.env`-Defaults.

## MySQL-Schema initial anlegen (Initialsetup / nach Wipe)
Wenn die MySQL-Tabellen fehlen, kannst du die Struktur gezielt per CLI neu anlegen:

```bash
python -m src.scripts.init_mysql_schema
```

Hinweis:
- Der Befehl nutzt das aktive oder gefallbackte Ziel aus der MySQL-Resolver-Logik.
- Für gezielte Initialisierung pro Ziel steht intern `initialize_mysql_schema_for_target("local"|"uni")` bereit.
- Falls das Schema selbst neu erstellt werden soll, setze `LOCAL_MYSQL_CREATE_DATABASE=true` oder `UNI_MYSQL_CREATE_DATABASE=true`.
- Alternativ zentral per Script: `.\mercator.ps1 init-db`.

## Docker-Start für lokale Tests (App + MongoDB + MySQL)
Für einen Klick-Start/Stop in Docker Desktop liegt eine Compose-Datei unter `mercator-compose.yml`.

```bash
docker compose -f mercator-compose.yml up -d
```
```bash
docker compose -f mercator-compose.yml down
```

Hinweise:
- Mit `up -d` starten drei Services: Streamlit-App (`http://localhost:8501`), MongoDB und lokale MySQL (`mysql:8`).
- Innerhalb von Compose nutzt die App automatisch `MONGO_URI=mongodb://mongo:27017/`.
- Innerhalb von Compose wird `MYSQL_ACTIVE_TARGET=local` und `LOCAL_MYSQL_HOST=mysql` gesetzt, damit die lokale DB im Stack erreichbar ist.
- Für native Runs außerhalb Docker kann `LOCAL_MYSQL_HOST=localhost` in `.env` unverändert bleiben.
- Persistenz erfolgt über die Volumes `mongo_data` und `mysql_data`.

## Render Review Deployment
- Render nutzt das bestehende `Dockerfile` als Docker Web Service (`render.yaml`).
- Die Review-Instanz ist oeffentlich erreichbar und nutzt den Healthcheck `/_stcore/health`.
- Setze fuer Review mindestens:
  - `APP_ENV=review`
  - `APP_TITLE=Mercator Review`
  - `MERCATOR_REVIEW_MODE=true`
  - `MERCATOR_DISABLE_IMPORT=true`
  - `MERCATOR_DISABLE_ADMIN_DELETE=true`
  - `MERCATOR_UI_TEST_MODE=true`
- Setze zusaetzlich externe Ziele/Secrets fuer Datenquellen:
  - `MYSQL_ACTIVE_TARGET`, `MONGO_ACTIVE_TARGET`
  - `LOCAL_MYSQL_HOST`, `LOCAL_MYSQL_PORT`, `LOCAL_MYSQL_DATABASE`, `LOCAL_MYSQL_USER`, `LOCAL_MYSQL_PASSWORD`
  - `LOCAL_MONGO_URI`, `LOCAL_MONGO_DATABASE`
  - `FMP_API_KEY`
- In Review Mode sind Import und Delete serverseitig blockiert (read-only Sicherheit).
- Nach Deploy testen: Healthcheck, Navigation aller Seiten, Explorer/Ticker-Detail ohne Score-KeyError.

Siehe auch: `docs/deployment/render_review.md`.

## UI Testing mit GPT-Agent
- Verwende die oeffentliche Render-URL ohne Login-Pflicht.
- Stelle sicher, dass Review Mode aktiv ist (`MERCATOR_REVIEW_MODE=true`).
- Halte Seitentitel und Navigation stabil (`Dashboard`, `Explorer`, `Ticker-Detailansicht`, `Admin`).
- Destruktive Aktionen (Import/Delete) muessen deaktiviert bleiben.
- Falls CDN/WAF vorgeschaltet ist, Agent-Traffic fuer Browser-Navigation zulassen.

### Docker-Stack komplett zurücksetzen
Wenn du Container sowie lokale MongoDB- und MySQL-Daten frisch neu aufsetzen willst, entferne den Stack inklusive Volumes und starte danach neu:

```powershell
docker compose -f mercator-compose.yml down -v
# Oder via Skript fuer gezielte Bereinigung von Altlasten:
.\mercator.ps1 cleanup
```

### Fehlerbehandlung: Port-Konflikte
Falls `.\mercator.ps1 restart` oder `start` mit `ExitCode 1` und einer Meldung wie `Bind for 0.0.0.0:3306 failed: port is already allocated` fehlschlägt:
1. Pruefe, ob noch alte Container (`mercator-mysql`, `mercator-mongo`, `mercator-app-1`) laufen.
2. Fuehre `.\mercator.ps1 cleanup` aus, um diese gezielt zu entfernen.
3. Starte den Stack danach erneut mit `.\mercator.ps1 start`.
```powershell
.\mercator.ps1 start
```

Danach kannst du den Status prüfen oder die App öffnen:

```powershell
.\mercator.ps1 status
.\mercator.ps1 open
```

## Nächste Schritte
- Scheduler für stündlichen Importlauf ergänzen.
- Gate-Regeln fachlich verfeinern.
- Zusätzliche Auswertungen für Präsentation und Bericht ergänzen.

## Hinweise zu Datensatz, MySQL und MongoDB
- FMP-MVP nutzt im Kern **zwei Endpunktklassen**:
  - `/insider-trading/latest`
  - `/profile-cik` (primär) + `/profile` (Fallback)
- Optionaler manueller Backfill je Firma: `/insider-trading/search`.
- MongoDB speichert Rohdaten und Profilpayloads.
- MySQL speichert bereinigte, auswertbare Zieldaten.
- Uni-Zugangsdaten dürfen nur über `.env` gesetzt werden und nicht ins Repository gelangen.

## Hinweise für Präsentation und Bericht
- Methodik-Seite als roten Faden nutzen.
- Architektur aus `docs/architecture.md` übernehmen.
- Berichtsfokus: Datenquelle, Datenfluss, Deduplizierung, Gate-Logik, Mehrwert der Zwei-DB-Architektur.

## TODO / offene Punkte
- Zentrale Liste: `docs/todos_offene_fragen.md`.
