# Architektur: Mercator

## Schichtenmodell
Das Projekt folgt einem klaren Schichtenmodell zur Trennung von Belangen:

1.  **Configuration Layer (`src/config/`):** Zentrale Verwaltung von Umgebungsvariablen und App-Settings.
2.  **Data Source Layer (`src/data_sources/`):** Kapselung der externen FMP-API-Zugriffe.
3.  **Preprocessing Layer (`src/preprocessing/`):**
    *   **Cleaning:** Feldmapping und Transformation.
    *   **Normalization:** Typkonvertierung (Datum, Zahlen).
    *   **Deduplication:** Erzeugung technischer Schlüssel (`dedupe_key`).
    *   **Gate Evaluation:** Filterlogik für Relevanz.
4.  **Database Layer (`src/db/`):**
    *   **MongoDB:** Dokumentenbasierte Speicherung von Rohdaten (`insider_trades_raw`) und Profilen (`companies`).
    *   **MySQL:** Relationale Speicherung bereinigter Daten für Abfragen und Visualisierungen.
5.  **Service Layer (`src/services/`):** Business-Logik für Import, Analyse und Dashboard-Aufbereitung.
6.  **UI Layer (`src/ui/`):** Streamlit-basierte Benutzeroberfläche mit Sidebar-Navigation und spezialisierten Seitenmodulen.

## Datenfluss (Import)
1.  **Abruf:** `FmpClient` lädt Insider-Feed (limit=100).
2.  **Verarbeitung:** `ImportService` orchestriert Normalisierung und Gate-Prüfung.
3.  **Roh-Speicherung:** Alle transformierten Datensätze werden in MongoDB gesichert.
4.  **Profil-Anreicherung:** Für Datensätze mit `Gate-PASS` wird das Unternehmensprofil via API geladen (sofern nicht im 7-Tage-Cache).
5.  **Ziel-Speicherung:** Bereinigte Trades und Profile werden in MySQL persistiert.
6.  **Visualisierung:** Streamlit-Seiten greifen ausschließlich über den Service-Layer auf die Daten zu.

## In-App-Konfiguration
Nutzer können über die Sidebar zwischen einer **Standard-Ansicht** (fokussiert) und einer **Advanced-Ansicht** (technische Details) umschalten. Dies steuert die Informationsdichte in Tabellen und Detailseiten.
