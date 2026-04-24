# Mercator

## Kurzbeschreibung
Mercator ist eine interaktive Datenanwendung für das Modul **Datenbanken 2**. Die Anwendung verarbeitet öffentlich verfügbare Insider-Trade-Daten und stellt sie in einer Streamlit-Oberfläche analysierbar dar.

## Ziel der Anwendung
1. öffentliche Finanzdaten laden (FMP API)
2. Rohdaten in MongoDB speichern
3. bereinigte Daten in MySQL speichern
4. Ergebnisse interaktiv in Streamlit visualisieren
5. Methodik und Datenfluss für akademische Zwecke transparent machen

## Nachweis der Kursanforderungen

| Anforderung | Umsetzung |
|---|---|
| Öffentliche Datenquelle / API | FMP API (insider-trading/latest, /profile-cik, /historical-price-eod/full) |
| Pandas-Verarbeitung | Normalisierung, Gate-Filter, 3-Tage-Akkumulation in `AccumulationService` |
| MySQL | Clean Store: Trades, Profile, Gate-Entscheide in `mercator_local` |
| MongoDB | Raw Store: JSON-Rohdaten je API-Antwort in `mercator` |
| Lesen aus beiden DBs | Dashboard/Explorer lesen aus MySQL; Admin zeigt MongoDB-Rohzähler |
| Interaktive Streamlit-Widgets | Filter, Selectbox, Datumsbereich, Toggle, Paginierung auf allen Seiten |
| Mindestens ein sinnvoller Chart | Sektor-Verteilung (Torte) und Netto-Signal-Chart (Balken) im Dashboard |
| Analytischer Mehrwert | Gate-Prüfung, Score-Modell (A-E), 3-Tage-Akkumulation, Trends über Zeit |

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
- `streamlit_app.py` – Einstiegspunkt (Bootstrap, Navigation, Page-Dispatch)
- `src/app/` – Bootstrap, Navigation, Auto-Import-Logik
- `src/config/` – App-, API- und DB-Konfiguration
- `src/data_sources/` – FMP-Client (Kern-Provider); Alpha Vantage & Polygon optional
- `src/preprocessing/` – Cleaning, Normalization, Deduplication, Gate-Evaluation
- `src/db/` – MongoDB-/MySQL-Clients und Repositories
- `src/services/` – Import-, Dashboard-, Analyse- und Einstellungs-Logik
- `src/ui/pages/` – Dashboard, Trade-Explorer, Unternehmen, Einstellungen, Methodik, Admin
- `src/ui/components/` – Wiederverwendbare UI-Bausteine
- `src/utils/` – Hilfsfunktionen (inkl. `format_mcap`, DataFrame-Utils)
- `tests/` – Unit-Tests (Filter, Auto-Import, Core-Logik)
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
    - Zeitlicher Abstand maximal 3 Kalendertage
7. Streamlit-Seiten lesen über `AnalysisService` aus den Repositories.
8. Optional kann im Admin ein `Raw -> Clean Sync` (ohne neue API-Calls) ausgelöst werden.

## UI & Features

Die App besteht aus folgenden Seiten (Sidebar-Navigation):

| Seite | Zweck |
|---|---|
| **📊 Dashboard** | Kennzahlen-Übersicht, Sektor-Verteilung, Volumen-Trends |
| **🕵️ Trade-Explorer** | Operative Hauptarbeitsfläche – Filterbarer Trade-Screener mit Drilldown |
| **🏢 Unternehmen** | Unternehmens-Übersicht mit Aggregationsfeldern (Trade-Count, letzter Trade) |
| **⚙️ Einstellungen** | Fachliche Regelwerke (Gate-Policy, Score-Schwellen) |
| **📖 Methodik** | Technische Dokumentation der Pipeline und des Scoring-Modells |
| **🛠️ Admin** | Import-Steuerung, Scheduler, Datenbank-Status und Wartung |

### Trade-Explorer Filter
- Symbol (LIKE-Suche auf `symbol_at_trade`)
- Insider-Name, Gate-Status, Validierungs-Status
- Richtung (Kauf/Verkauf), Mindestscore
- Trade Republic Universe Status
- Datumsbereich

### Auto-Import Scheduler
- Konfigurierbar im Admin-Tab „Import-Konfiguration"
- Folgt `RuntimeSettings`: `auto_import_enabled`, `auto_import_interval_minutes`, `auto_import_on_start`
- Deaktiviert per Default (sicherer Start)

## Lokale Einrichtung
### Windows (Normale cmd.exe oder PowerShell – empfohlen)
Wenn du **nur testen/starten** willst, brauchst du lokal **kein Python**, solange Docker Desktop läuft.

```cmd
REM Im Windows Terminal (cmd.exe oder PowerShell)
git clone <this-repo-url> mercator
cd mercator
copy .env.example .env
mercator.bat start
```

oder in PowerShell:
```powershell
git clone <this-repo-url> mercator
cd mercator
Copy-Item .env.example .env -Force
.\mercator.ps1 start
```

### Windows + Git Bash / WSL
Falls du Git Bash oder WSL installiert hast:

```bash
git clone <this-repo-url> mercator
cd mercator
cp .env.example .env
chmod +x mercator
./mercator start
```

### macOS / Linux (Bash)
```bash
git clone <this-repo-url> mercator
cd mercator
cp .env.example .env
chmod +x mercator
./mercator start
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
- `MONGO_ACTIVE_TARGET` (`local` oder `uni`)
- `MONGO_AUTO_FALLBACK_TO_LOCAL` (`true`/`false`)
- Für `local`: `LOCAL_MONGO_URI`, `LOCAL_MONGO_DATABASE` (Fallback kompatibel: `MONGO_URI`, `MONGO_DATABASE`)
- Für `uni`: `UNI_MONGO_URI`, `UNI_MONGO_DATABASE` (Pflicht bei `MONGO_ACTIVE_TARGET=uni`)
- `FMP_API_KEY`
- `APP_ENV`, `APP_TITLE`, `DATASET_PATH`

Kompatibilität:
- Bestehende `MYSQL_*` Variablen werden weiter als Fallback für das lokale Ziel unterstützt.
- Für Mongo gilt: `authSource=admin` im URI ist nur die Auth-DB; die Zieldatenbank bleibt `*_MONGO_DATABASE`.
- Mongo-Fallback ist transparent und greift nur bei `MONGO_ACTIVE_TARGET=uni` optional auf `local` zurück.

Optionale Import-/Gate-Parameter:
- `GATE_MIN_TRADE_VALUE` (Default `100000` – Mindestwert $100.000)
- `GATE_REQUIRE_PURCHASE_EVENT` (`true`/`false`)
- `GATE_REQUIRE_COMMON_STOCK` (`true`/`false`)
- `PROFILE_GATE_FILTER_STATUSES` (CSV, z. B. `PASS` oder `PASS,PENDING`)
- `MERCATOR_DEMO_MODE` (`true`/`false`, Default `false`) – blockiert destruktive Admin-Aktionen serverseitig

## Öffentliche Freigabe (lokale Demo/Test-Shares)
- Zweck: kurzfristige, öffentliche Freigabe einer **lokal laufenden** Streamlit-Instanz für Demo- und Testzwecke.
- Standardprovider: **Cloudflare Quick Tunnel** via `cloudflared`.
- **Execution Mode**:
  - `host` (**empfohlen**): cloudflared läuft auf dem Host, robust gegen Container→Edge-Netzpfadprobleme.
  - `container` (Fallback): cloudflared läuft wie bisher im App-Container.
- UI-Orte:
  - Sidebar (unter „Verwaltung & Hilfe“): Status + Start/Stop (primäre Aktion) + Öffnen + Sprung in Admin.
  - Admin-Bereich, Tab **„Öffentliche Freigabe“**: Diagnose, Log-Tail, Detailinfos.
- Sicherheitsrahmen: nur temporär nutzen; die erzeugte URL ist extern erreichbar.

### Voraussetzungen
- `cloudflared` muss installiert und im PATH verfügbar sein (oder via `CLOUDFLARED_BIN` gesetzt).
- App läuft lokal (z. B. `http://localhost:8501`).

Installationshilfe (Cloudflare):
- https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

### Relevante ENV-Variablen
- `ENABLE_PUBLIC_SHARE=true|false` (Default: `false`)
- `PUBLIC_SHARE_PROVIDER=cloudflare` (aktuell vollständig implementiert)
- `PUBLIC_SHARE_EXECUTION_MODE=host|container` (Default: `host`)
- `PUBLIC_SHARE_LOCAL_URL=http://localhost:8501` (optional)
- `CLOUDFLARED_BIN=cloudflared` (optional, z. B. absoluter Pfad)
- `PUBLIC_SHARE_STARTUP_TIMEOUT_SECONDS=20` (optional)
- `PUBLIC_SHARE_STARTUP_GRACE_SECONDS=15` (optional, toleriert DNS/Edge-Propagation direkt nach Tunnelstart)
- `PUBLIC_SHARE_HEALTHCHECK_TIMEOUT_SECONDS=2.0` (optional, kurzer Reachability-Check)
- `PUBLIC_SHARE_CLOUDFLARED_EXTRA_ARGS` (optional, z. B. `--protocol http2 --edge-ip-version 4`)
- `PUBLIC_SHARE_STATUS_FILE`, `PUBLIC_SHARE_LOG_FILE`, `PUBLIC_SHARE_PID_FILE` (Dateien für Host/Container-Diagnostik)

### Lokale Nutzung
1. App lokal starten.
2. Host-Modus (empfohlen):
   - `.\mercator.ps1 share-start`
   - `.\mercator.ps1 share-reset`
   - `.\mercator.ps1 share-stop`
3. Container-Modus:
   - weiterhin über Sidebar/Admin start/stop steuerbar.
3. Öffentliche URL teilen (im Admin-Feld Copy-freundlich markierbar; Öffnen-Button in Sidebar/Admin).
4. Nach Demo/Test **Freigabe stoppen** (Sidebar oder Admin).

### Troubleshooting
- **HTTP 530 / 1033 trotz laufendem Streamlit**: typischerweise Container→Cloudflare-Edge-Netzproblem (QUIC/HTTP2 in restriktiven Netzen). Wechsel auf `PUBLIC_SHARE_EXECUTION_MODE=host`.
- **`cloudflared` fehlt**: Status wird auf Fehler gesetzt; `CLOUDFLARED_BIN` prüfen.
- **Keine URL erhalten**: Start läuft in Timeout und beendet den Prozess sauber.
- **Tunnel stale**: Prozess wurde beendet oder Session veraltet; erneut starten.
- **Öffentliche URL nicht erreichbar**: Status „Warnung“ (Prozess läuft, URL antwortet aber nicht).

### Limitierungen
- Kein permanenter Tunnel, keine Zero-Trust-Policy-Absicherung.
- URL-Lebensdauer und Stabilität hängen vom Quick-Tunnel-Laufprozess ab.
- Aktuell nur Cloudflare Quick Tunnel aktiv; Architektur ist auf weitere Provider (z. B. ngrok, Managed Tunnel) vorbereitbar.


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
- Betroffene Tabellen: `companies`, `insider_trades`, `app_filter_settings`, `app_runtime_preferences`.
- Verfahren: SQL-basierte Upserts (`companies` über `company_key`, `insider_trades` über `dedupe_key`).
- Startup-Reconnect ist jetzt steuerbar über `MYSQL_STARTUP_SYNC_ENABLED=true|false`.
- Bei Start ohne aktive Uni-DB wird lokal `pending_uni_sync=true` markiert; beim nächsten erfolgreichen Uni-Start wird automatisch `local -> uni` synchronisiert.
- Stale-Running-Locks werden über `MYSQL_STARTUP_SYNC_STALE_MINUTES` automatisch aufgelöst.
- Der Sync wird nur über den Sidebar-Button ausgelöst, wenn `uni` erreichbar ist.

## Datenbank-Statusanzeigen in der UI
- MySQL- und MongoDB-Status werden getrennt angezeigt.
- Bei Uni-Ausfall mit erlaubtem Fallback wird der Wechsel auf `local` explizit ausgewiesen.
- Mongo nutzt denselben transparenten Resolver-Mechanismus wie MySQL (requested target, active target, fallback-Flag, Meldungen).
- Wenn nur MongoDB ausfällt, bleibt die App für MySQL-basierte Auswertungen nutzbar; Rohdatenspeicherung/Import ist dann eingeschränkt.

## Start der Anwendung
```bash
streamlit run streamlit_app.py
```

## Schnelleinstieg – Cheat Sheet

**Windows (cmd.exe oder PowerShell):**
```cmd
mercator.bat start
mercator.bat stop
mercator.bat restart
mercator.bat share-start
mercator.bat share-stop
mercator.bat share-reset
```

oder in PowerShell:
```powershell
.\mercator.ps1 start
.\mercator.ps1 stop
.\mercator.ps1 restart
.\mercator.ps1 share-start
.\mercator.ps1 share-stop
.\mercator.ps1 share-reset
```

**Bash / WSL / Linux:**
```bash
./mercator start
./mercator stop
./mercator restart
```

Oder ausführlich: Siehe [Steuerungsskripte-Übersicht](SKRIPTE.md).

## One-File Steuerung (Start/Stop/Restart)

### Für Windows Benutzer (Standard)
Nutze zentral `mercator.bat` oder `mercator.ps1`:

```cmd
mercator.bat start
mercator.bat stop
mercator.bat restart
mercator.bat share-start
mercator.bat share-stop
mercator.bat share-reset
```

### Für macOS / Linux Benutzer
Nutze `mercator`:

```bash
./mercator start
./mercator stop
./mercator restart
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
- `share-start` - startet den Public-Share-Tunnel
- `share-stop` - stoppt den Public-Share-Tunnel
- `share-reset` - startet den Public-Share-Tunnel sauber neu

Beispiele:

```powershell
.\mercator.ps1 restart
.\mercator.ps1 share-start
.\mercator.ps1 share-reset
.\mercator.ps1 share-stop
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
  - Optional fuer Live-Demos: `MERCATOR_DEMO_MODE=true`
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
- Halte Seitentitel und Navigation stabil (`Dashboard`, `Trades`, `Unternehmen`, `Unternehmens-Detail`, `Trade-Detail`, `Admin`).
- Destruktive Aktionen (Import/Delete) muessen deaktiviert bleiben.
- Fuer deterministische Agent-Webtests: Auto-Import muss deaktiviert bleiben (`MERCATOR_DISABLE_IMPORT=true` und/oder `MERCATOR_UI_TEST_MODE=true`).
- Falls CDN/WAF vorgeschaltet ist, Agent-Traffic fuer Browser-Navigation zulassen.

### Docker-Stack komplett zurücksetzen
Wenn du Container sowie lokale MongoDB- und MySQL-Daten frisch neu aufsetzen willst, entferne den Stack inklusive Volumes und starte danach neu:

```powershell
docker compose -f mercator-compose.yml down -v
```

### Fehlerbehandlung: Port-Konflikte
Falls `.\mercator.ps1 restart` oder `start` mit `ExitCode 1` und einer Meldung wie `Bind for 0.0.0.0:3306 failed: port is already allocated` fehlschlägt:
1. Pruefe, ob noch alte Container (`mercator-mysql`, `mercator-mongo`, `mercator-app-1`) laufen.
2. Fuehre `.\mercator.ps1 stop` aus, um laufende Stack-Container zu beenden.
3. Starte den Stack danach erneut mit `.\mercator.ps1 start`.
```powershell
.\mercator.ps1 start
```


## Nächste Schritte
- Scheduler für stündlichen Importlauf ergänzen.
- Gate-Regeln fachlich verfeinern.
- Zusätzliche Auswertungen für Präsentation und Bericht ergänzen.

## Hinweise zu Datensatz, MySQL und MongoDB
- FMP-MVP nutzt im Kern **zwei Endpunktklassen**:
  - `/insider-trading/latest`
  - `/profile` (Standard für Gate-Pass-Kandidaten; `/search-cik` und `/profile-cik` nur als optionale Fallbacks bei Identitäts- oder Symbolauflösungsproblemen)
- Optionaler manueller Backfill je Firma: `/insider-trading/search`.
- MongoDB speichert Rohdaten und Profilpayloads.
- MySQL speichert bereinigte, auswertbare Zieldaten.
- Uni-Zugangsdaten dürfen nur über `.env` gesetzt werden und nicht ins Repository gelangen.

## Hinweise für Präsentation und Bericht
- Methodik-Seite als roten Faden nutzen.
- Architektur aus `docs/architecture.md` übernehmen.
- Berichtsfokus: Datenquelle, Datenfluss, Deduplizierung, Gate-Logik, Mehrwert der Zwei-DB-Architektur.

## 5-Minuten Demo-Flow
1. **Dashboard**: KPI-Überblick und Chart zeigen (Analysecharakter).
2. **Methodik**: Pipeline, Raw/Clean-Trennung, Gate- und Scoring-Regeln erklären.
3. **Trades**: Filter anwenden, Gate/Score/Status textlich sichtbar demonstrieren.
4. **Unternehmen**: Firmenansicht und Trade-Historie zeigen.
5. **Admin Status**: Mongo Raw Store und MySQL Clean Store getrennt nachweisen; Sync-Status kurz erläutern.

## Troubleshooting (Kurz)
- **Mongo Raw Count = 0**: echten Import ausführen; Raw-Store wird nur im Importpfad befüllt.
- **MySQL online, Mongo fallback aktiv**: Mongo-Ziel/Netzwerk prüfen (`MONGO_ACTIVE_TARGET`, URI, DNS).
- **FMP 403**: API-Key ungültig/gesperrt -> Import stoppen, Key prüfen.
- **FMP 429**: Rate-Limit erreicht -> später erneut versuchen, Batch/Intervall reduzieren.
- **Public Share deaktiviert**: In Production/Review wird `ENABLE_PUBLIC_SHARE` serverseitig deaktiviert.

## TODO / offene Punkte


## FMP API Spec
Die verbindliche finale Spezifikation liegt in `docs/fmp_api_spec_v2_final.md`.
