# Mercator: Ablauf und Datenfluss

Diese Dokumentation beschreibt den technischen Ablauf der Datenverarbeitung, die Speicherstrategie und das Verhalten bei wiederholten API-Aufrufen.

## 1. High-Level Prozessablauf (Workflow)

Der Kernprozess ist der Import-Lauf, der Daten von der Financial Modeling Prep (FMP) API in das System überführt.

### Phase A: Datenerfassung (Ingestion)
1.  **API-Request**: Der `ImportService` ruft über den `FmpClient` den Endpunkt `Latest Insider Trading` ab.
2.  **Normalisierung**: Die erhaltenen JSON-Rohdaten werden unmittelbar durch `normalize_insider_trade` vorverarbeitet (Feld-Mapping, Typ-Konvertierung, Generierung eines `dedupe_key`).

### Phase B: Gate-Keeping & Staging
1.  **Gate-Evaluation**: Der `GateEvaluator` prüft jeden Trade gegen fachliche Regeln (z.B. Symbol vorhanden?). Er entscheidet, ob für dieses Symbol ein Profil-Update notwendig ist.
2.  **Raw-Persistence (MongoDB)**: Die normalisierten Trades werden in die MongoDB-Collection `insider_trades_raw` geschrieben.
    *   **Idempotenz**: Durch den `dedupe_key` werden bereits bekannte Transaktionen nicht doppelt verarbeitet.

### Phase C: Firmenprofil-Synchronisation
Für jeden relevanten Trade wird das Firmenprofil verwaltet:
1.  **Cache-Check**: Es wird in MongoDB geprüft, ob ein Profil für das Symbol existiert und ob es jünger ist als die konfigurierte `PROFILE_TTL_DAYS`.
2.  **API-Fallback**: Nur wenn kein gültiges Profil vorliegt, wird der FMP-Endpunkt `Company Profile` aufgerufen.
3.  **Duales Upsert**: Das neue/aktualisierte Profil wird sowohl in **MongoDB** (als Full-Payload) als auch in **MySQL** (strukturiert für die UI) gespeichert.

### Phase D: Core-Persistence (MySQL)
1.  **Trade-Insert**: Die Transaktionen werden in die MySQL-Tabelle `insider_trades` geschrieben.
2.  **Bereitstellung**: Die Daten stehen nun dem `DashboardService` und `AnalysisService` für die Streamlit-UI zur Verfügung.

---

## 2. Speicherkonzept (Datenhaltung)

Das Projekt nutzt einen hybriden Ansatz aus dokumentenbasierter und relationaler Speicherung:

### MongoDB (Rohdaten & Dokument-Archiv)
*   **Zweck**: Flexibler Speicher für API-Antworten und semi-strukturierte Daten.
*   **Collections**:
    *   `insider_trades_raw`: Archiv aller jemals gesehenen Insider-Trades inklusive technischer Metadaten.
    *   `companies`: Cache für Firmenprofile (speichert das komplette JSON-Original-Payload im Feld `profile_payload`).

### MySQL (Strukturierte Daten & Analytics)
*   **Zweck**: Performante Abfragen, Filterung und Aggregation für die Benutzeroberfläche.
*   **Tabellen**:
    *   `companies`: Enthält die wichtigsten Firmen-KPIs (Market Cap, Sektor, Industrie, etc.).
    *   `insider_trades`: Enthält die bereinigten Transaktionsdaten, verknüpft über das `symbol`.

---

## 3. Verhalten bei wiederholten API-Aufrufen (Idempotenz)

Das System ist darauf ausgelegt, robust gegenüber mehrfachen Aufrufen oder redundanten API-Daten zu sein:

### Szenario: Der gleiche Trade wird erneut von der API geliefert
*   **Mechanismus**: Jede Transaktion erhält einen eindeutigen `dedupe_key` (Hash/String aus Symbol, Datum, Menge, Preis und Reporting-Name).
*   **Ergebnis**:
    *   **MongoDB**: `update_one` mit `$setOnInsert` verhindert das Überschreiben bestehender Rohdaten.
    *   **MySQL**: `ON DUPLICATE KEY UPDATE` stellt sicher, dass der Datensatz aktuell bleibt, aber keine Dublette entsteht.

### Szenario: Ein zweiter Call für eine einzelne Firma (Company Profile)
*   **Mechanismus**:
    1.  **TTL-Schutz**: Bevor die API angefragt wird, prüft das System den Zeitstempel `profile_updated_at` in der MongoDB. Innerhalb der `PROFILE_TTL_DAYS` (Standard: 7 Tage) erfolgt **kein** neuer API-Aufruf.
    2.  **Erzwungener Upsert**: Falls ein Aufruf erfolgt (z.B. weil die TTL abgelaufen ist oder das Profil fehlte), wird das Profil per Upsert aktualisiert.
*   **Ergebnis**: Bestehende Firmendaten in MySQL und MongoDB werden mit den neuesten Werten überschrieben. Historische Profilzustände werden im aktuellen MVP nicht versioniert (nur der jeweils neueste Stand ist in MySQL sichtbar).

---

## 4. Übersicht der Systemkomponenten

| Komponente | Aufgabe |
| :--- | :--- |
| **Streamlit App** | Benutzeroberfläche und Dashboard-Visualisierung. |
| **Import Service** | Koordiniert den Datenfluss zwischen API und Datenbanken. |
| **Cleaning Service** | Bereinigt und transformiert Daten (Teil des Preprocessing). |
| **Gate Evaluator** | Filtert Daten und steuert die Logik des Profil-Abrufs. |
| **Repositories** | Abstrahieren den Zugriff auf MySQL und MongoDB. |
| **FMP Client** | Kapselt die HTTP-Kommunikation mit der Datenquelle. |
