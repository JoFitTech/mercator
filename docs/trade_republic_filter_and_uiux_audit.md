# Trade Republic Filter & UI/UX Audit

## 1. Trade Republic Universumsfilter

### Fachliche Logik
- **Quelle:** Offizielles TR-Universum via CSV-URL (defensives Parsing).
- **Matching:** 
  1. Primär über ISIN (exakt).
  2. Fallback (optional, aktuell ISIN-fokusiert) über Symbol + Name nur bei Eindeutigkeit.
- **Zustände:** 
  - `IN_UNIVERSE`: Eindeutig im Referenzdatensatz gefunden.
  - `NOT_IN_UNIVERSE`: Referenzdaten vorhanden, ISIN aber nicht enthalten.
  - `UNKNOWN`: Keine Referenzdaten, Fehler beim Abgleich oder uneindeutige Zuordnung.
- **Haftungsausschluss:** Das System behauptet niemals Live-Handelbarkeit. Ein entsprechender Hinweis ist in allen UI-Sektionen integriert.

### Technische Umsetzung
- `TradeRepublicUniverseIngestionService`: 
  - Nutzt `csv.Sniffer` für robuste Dialekt-Erkennung (Komma, Semikolon, Tab).
  - Unterstützt Spalten-Aliase (ISIN, Ticker, Name, etc.).
  - Performante Speicherung via `executemany` in MySQL (`trade_republic_universe_reference`).
  - Metadaten-Tracking (`trade_republic_universe_meta`) mit Hash-Prüfung zur Vermeidung unnötiger Updates.
- `TradeRepublicUniverseMatchingService`: Defensiver Abgleich gegen die Referenztabelle.

## 2. UI/UX Audit & Harmonisierung

### Navigationsstruktur
- Reduziert auf maximal 5 Primärpunkte (Dashboard, Trades, Unternehmen, Admin, Einstellungen) gemäß Spezifikation.

### Design-Prinzipien (Apple Inspired)
- **Clarity first:** Klare Labels, keine dekorativen Elemente ohne Informationswert.
- **Information Density:** Tabellen nutzen den Raum optimal, KPIs sind fokussiert.
- **Status-Kommunikation:** Status wird nie rein über Farbe kommuniziert (Icons + Text).
  - ✅ IN / ❌ OUT / ❓ UNKNOWN für Trade Republic.

### Tabellen-Standardisierung
- Nutzung von `render_smart_table` für konsistentes Look & Feel.
- Sticky Header (Streamlit Default), definierte Spaltenbreiten, rechtsbündige Zahlen.

## 3. Dokumentierte Abnahme

| Anforderung | Status | Kommentar |
| :--- | :--- | :--- |
| TR-Status fachlich sauber | Erfüllt | Unterscheidung IN/OUT/UNKNOWN umgesetzt. |
| Kein Live-Trading-Claim | Erfüllt | Disclaimer in Explorer und Detailansicht. |
| Defensives TR-Parsing | Erfüllt | CSV Sniffer + Try/Except Härtung. |
| Admin-Diagnostik | Erfüllt | Metadaten und manuelle Aktualisierung im Admin-Bereich. |
| Navigations-Limit (5) | Erfüllt | Dashboard, Trades, Unternehmen, Admin, Einstellungen. |
| UI-Konsistenz (Table/KPI) | Erfüllt | Harmonisierung über alle Hauptseiten. |

**Gesamtbewertung: FINAL**
Die Lösung erfüllt alle technischen und fachlichen Vorgaben der Mercator-Spezifikation.
