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
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Umgebungsvariablen
Siehe `.env.example`.

Pflichtvariablen:
- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`
- `MONGO_URI`, `MONGO_DATABASE`
- `FMP_API_KEY`
- `APP_ENV`, `APP_TITLE`, `DATASET_PATH`

## Start der Anwendung
```bash
streamlit run streamlit_app.py
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
