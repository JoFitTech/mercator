# Mercator

## 1) Kurzbeschreibung
Mercator ist eine interaktive Streamlit-Datenanwendung zur Analyse öffentlich verfügbarer Finanzdaten. Der Fokus liegt auf der Verarbeitung, Speicherung und Visualisierung von Insider-Trade-Daten bzw. ähnlichen Finanzereignisdaten. Die Anwendung dient als Uni-Projekt im Modul Datenbanken 2 und demonstriert den Einsatz von Pandas, MySQL, MongoDB und Streamlit in einer durchgängigen Datenpipeline.

## 2) Ziel der Anwendung
Die Anwendung soll einen öffentlich verfügbaren Datensatz einlesen, bereinigen, in zwei unterschiedlichen Datenbanksystemen speichern und anschließend in einer interaktiven Weboberfläche analysierbar machen. Ziel ist es, Datenexploration, Visualisierung und nachvollziehbare Datenverarbeitung in einer kompakten, akademisch sauberen Anwendung zu verbinden.

## 3) Uni-Kontext und fachlicher Scope
### Im Scope
- Import eines öffentlichen Datensatzes
- Aufbereitung mit Pandas
- Speicherung in MongoDB und MySQL
- Interaktive Analyse mit Streamlit
- Visualisierung zentraler Muster und Zusammenhänge
- Fokus auf Insider-Trades oder ähnliche Finanzdaten
- bewusste Reduktion auf einen klaren akademischen Kern

### Nicht Teil des Scopes
- Broker-Anbindung
- Live-Trading
- Login-System
- E-Mail-Automation
- komplexe Produktplattform-Funktionen
- Realtime-Marktdatenarchitektur

## 4) Verwendete Technologien
- Python 3.x
- Streamlit
- Pandas
- MySQL (relationale Speicherung)
- MongoDB (Rohdatenablage)
- python-dotenv

## 5) Projektstruktur

| Pfad | Zweck |
|---|---|
| `streamlit_app.py` | Einstiegspunkt der Streamlit-Anwendung mit Navigation und Routing. |
| `src/config/` | Zentrale Konfiguration und Laden von Umgebungsvariablen. |
| `src/data_sources/` | Einlesen von Datensätzen (lokale Dateien, später ggf. weitere Quellen). |
| `src/preprocessing/` | Bereinigung, Normalisierung und Transformation mit Pandas. |
| `src/db/` | DB-Clients und Repository-Schnittstellen für MySQL und MongoDB. |
| `src/services/` | Fachliche Orchestrierung (Import, Analyse, Dashboard-Aufbereitung). |
| `src/ui/` | Seitenmodule und Komponenten für die Streamlit-Oberfläche. |
| `src/models/` | Lesbare Domänenmodelle (`InsiderTrade`, `Company`, `AnalysisResult`). |
| `src/utils/` | Allgemeine Hilfsfunktionen (Logging, Datum, DataFrames). |
| `data/` | Lokale Datenablage (`raw`, `interim`, `processed`). |
| `docs/` | Projektdokumentation (Scope, Architektur, Datensatznotizen). |
| `tests/` | Basistests und Platzhaltertests. |
| `legacy/` | Geordnet ausgelagerte Altbestände außerhalb des aktuellen Uni-Scopes. |

## 6) Datenfluss
1. Datensatz wird in `data/raw/` abgelegt.
2. Import über `DatasetLoader`.
3. Bereinigung/Normalisierung mit Modulen in `src/preprocessing/`.
4. Rohdaten werden in MongoDB gespeichert.
5. Bereinigte Daten werden in MySQL gespeichert.
6. Streamlit liest Daten/Ergebnisse und stellt Dashboard + Explorer bereit.

## 7) Einrichtung lokal
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## 8) Umgebungsvariablen
Siehe `.env.example` als Vorlage.

Relevante Variablen:
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MONGO_URI`
- `MONGO_DATABASE`
- `APP_ENV`
- `APP_TITLE`
- `DATASET_PATH`

## 9) Start der Anwendung
```bash
streamlit run streamlit_app.py
```

## 10) Geplante nächste Schritte
1. Finalen öffentlichen Datensatz auswählen und dokumentieren.
2. Persistenzmethoden in `mysql_repository.py` und `mongo_repository.py` produktiv implementieren.
3. Datenmodell und SQL-Schema auf finalen Spaltenkatalog ausrichten.
4. Weitere Kennzahlen/Visualisierungen für die Präsentation ergänzen.
5. Ergebnisabschnitte für den Projektbericht iterativ befüllen.

## 11) Hinweise zum Datensatz
- Der finale Datensatz ist noch nicht festgelegt.
- In `docs/dataset_notes.md` sind offene Punkte und Mapping-Ideen dokumentiert.
- Solange kein finaler Datensatz feststeht, sind einige Verarbeitungsregeln bewusst als TODO markiert.

## 12) Hinweise zu MySQL und MongoDB
- MySQL: Zielsystem für bereinigte, auswertbare Struktur.
- MongoDB: Ablage semistrukturierter oder roher Eingabedaten.
- Ohne laufende DB-Instanzen zeigt die App einen klaren Hinweis an, statt still zu scheitern.

## 13) Hinweise für Präsentation und Bericht
- Methodik-Seite in der App als Demo-Narrativ verwenden.
- Architektur aus `docs/architecture.md` als Basis für Schaubilder nutzen.
- Für den 5–10-seitigen Bericht: Problemstellung, Datenquelle, Pipeline, DB-Design, UI und Erkenntnisse getrennt darstellen.
