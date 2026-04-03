# Mercator

## Kurzbeschreibung
Mercator ist eine interaktive Datenanwendung für das Modul **Datenbanken 2**. Die Anwendung verarbeitet öffentlich verfügbare Insider-Trade-Daten und stellt sie in einer Streamlit-Oberfläche analysierbar dar.

## Ziel der Anwendung
1. öffentliche Finanzdaten laden
2. Rohdaten in MongoDB speichern
3. bereinigte Daten in MySQL speichern
4. Ergebnisse interaktiv in Streamlit visualisieren

## Uni-Kontext und Scope
Mercator ist bewusst als akademisches MVP ausgelegt:
- Fokus auf nachvollziehbaren Datenfluss
- klare Trennung von Roh- und Zieldaten
- keine Produkt-/Enterprise-Nebenziele

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
- `src/data_sources/` – FMP-API-Client
- `src/preprocessing/` – Normalisierung, Dedupe-Key, Gate-Evaluation
- `src/db/` – MongoDB-/MySQL-Clients und Repositories
- `src/services/` – Import-, Dashboard- und Analyse-Logik
- `src/ui/pages/` – Dashboard, Explorer, Ticker-Detail, Methodik
- `src/utils/` – Hilfsfunktionen
- `docs/` – Scope, Architektur, Datensatznotizen
- `tests/` – robuste Basistests
- `legacy/` – geordnete Altbestände

## Datenfluss
1. `ImportService` lädt `Latest Insider Trading` von FMP (`page=0`, `limit=100`).
2. Rohobjekte werden normalisiert, typisiert und dedupliziert.
3. Rohdaten landen in MongoDB (`insider_trades_raw`).
4. Gate-Pass-Kandidaten lösen optionalen Profilabruf aus (`/profile`), inkl. 7-Tage-Cache.
5. Bereinigte Trades und Profile werden in MySQL gespeichert.
6. Streamlit-Seiten lesen über Services aus den Repositories.

## Lokale Einrichtung
### Windows PowerShell (empfohlen)
Wenn du **nur testen/starten** willst, brauchst du lokal **kein Python**, solange Docker Desktop laeuft.

```powershell
Set-Location "C:\Users\josef.lautner\Source\IdeaProjects\Privat\mercator"
Copy-Item .env.example .env -Force
.\mercator.ps1 start
.\mercator.ps1 open
```

Wichtig:
- In PowerShell musst du lokale Skripte mit **`.\mercator.ps1 start`** aufrufen.
- `source` ist ein Bash-Befehl und funktioniert in PowerShell nicht.
- Wenn `python`, `pip` oder `streamlit` nicht gefunden werden, ist lokal noch kein Python installiert. Fuer den Docker-Start ist das aber **nicht noetig**.

### Lokale Python-Umgebung (nur wenn du ohne Docker entwickeln willst)
```powershell
Set-Location "C:\Users\josef.lautner\Source\IdeaProjects\Privat\mercator"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env -Force
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


## MySQL-Target-Switch (local/uni)
- Mercator kennt zwei MySQL-Ziele: `local` (Docker/Entwicklung) und `uni` (Uni-DB).
- Das aktive Ziel wird per `MYSQL_ACTIVE_TARGET` gewählt.
- Wenn `MYSQL_ACTIVE_TARGET=uni` gesetzt ist und die Uni-DB nicht erreichbar ist, kann optional auf `local` zurückgefallen werden (`MYSQL_AUTO_FALLBACK_TO_LOCAL=true`).
- Der Fallback ist technisch transparent: der Resolver liefert Hinweise, statt still zu verschleiern.
- Ohne Uni-WLAN funktioniert in der Regel nur `local`, sofern kein externer Zugriff auf die Uni-DB möglich ist.

## Kontrollierter MySQL-Sync
- Sync ist explizit und standardmäßig deaktiviert (`MYSQL_SYNC_ENABLED=false`).
- Default-Richtung im aktuellen Stand: `local -> uni`.
- Betroffene Tabellen: `companies` und `insider_trades`.
- Verfahren: SQL-basierte Upserts (`companies` über `symbol`, `insider_trades` über `dedupe_key`).
- Es gibt **keinen** automatischen Hintergrund-Sync beim App-Start.

## Start der Anwendung
```bash
streamlit run streamlit_app.py
```

## One-File Steuerung (Start/Stop/Restart)
Nutze zentral `mercator.ps1`, um den lokalen Stack und den DB-Init zu steuern.

```powershell
Set-Location "C:\Users\josef.lautner\Source\IdeaProjects\Privat\mercator"
.\mercator.ps1 start
```

Verfuegbare Aktionen:
- `start` - startet App + Mongo per Compose
- `stop` - stoppt den Stack
- `restart` - startet den Stack neu
- `status` - zeigt Containerstatus
- `logs` - streamt Logs (default Service `app`)
- `init-db` - fuehrt MySQL-Schema-Init im App-Container aus
- `open` - oeffnet `http://localhost:8501`

Beispiele:

```powershell
.\mercator.ps1 status
.\mercator.ps1 restart
.\mercator.ps1 logs
.\mercator.ps1 logs -Service mongo
.\mercator.ps1 init-db
```

In der Dashboard-Seite kannst du unter **Import- und Gate-Konfiguration** die API-Parameter (page/limit)
und den Profilabruf-Filter zur Laufzeit anpassen. Das ueberschreibt die Code-/`.env`-Defaults nur fuer den aktuellen Lauf.

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

## Docker-Start für lokale Tests (App + MongoDB)
Für einen Klick-Start/Stop in Docker Desktop liegt eine Compose-Datei unter `mercator-compose.yml`.

```bash
docker compose -f mercator-compose.yml up -d
```
```bash
docker compose -f mercator-compose.yml down
```

Hinweise:
- Mit `up -d` starten zwei Services: Streamlit-App (`http://localhost:8501`) und MongoDB.
- Die App nutzt weiter die MySQL-Verbindung aus `.env` (z. B. Uni-MySQL).
- Innerhalb von Compose nutzt die App automatisch `MONGO_URI=mongodb://mongo:27017/`.
- Persistenz erfolgt über das Volume `mongo_data`.

### Docker-Stack komplett zurücksetzen
Wenn du Container und die lokale MongoDB frisch neu aufsetzen willst, entferne den Stack inklusive Volume und starte danach neu:

```powershell
docker compose -f mercator-compose.yml down -v
docker compose -f mercator-compose.yml up -d
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
- FMP-MVP nutzt **nur zwei Endpunkte**:
  - `/insider-trading/latest`
  - `/profile`
- MongoDB speichert Rohdaten und Profilpayloads.
- MySQL speichert bereinigte, auswertbare Zieldaten.
- Ohne DB-Verbindung zeigt die UI eine verständliche Fehlermeldung.

## Hinweise für Präsentation und Bericht
- Methodik-Seite als roten Faden nutzen.
- Architektur aus `docs/architecture.md` übernehmen.
- Berichtsfokus: Datenquelle, Datenfluss, Deduplizierung, Gate-Logik, Mehrwert der Zwei-DB-Architektur.

## TODO / offene Punkte
- Zentrale Liste: `docs/todos_offene_fragen.md`.
