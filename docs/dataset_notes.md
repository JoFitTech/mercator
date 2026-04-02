# Datensatz-Notizen

## Platz für Datensatzbeschreibung
- TODO: Finalen Datensatz benennen (Quelle, Lizenz, Aktualisierungsintervall).
- TODO: Spaltenkatalog dokumentieren.

## Geplanter Importweg
1. Download / Bereitstellung in `data/raw/`
2. Einlesen über `DatasetLoader`
3. Bereinigung und Normalisierung im `preprocessing`-Paket
4. Speicherung in MongoDB (roh) und MySQL (bereinigt)

## Offene Punkte
- TODO: Primärschlüsseldefinition für MySQL-Tabelle
- TODO: Deduplizierungsstrategie für Mehrfachimporte
- TODO: Behandlung fehlender Werte je Spalte

## Mapping- und Bereinigungsideen
- Ticker: trim + uppercase
- Datum: robustes Parsing (`errors='coerce'`)
- Zahlenfelder: `to_numeric` mit defensiver Fehlerbehandlung

## Hinweis
Finale Regeln werden erst nach Entscheidung für den konkreten Datensatz festgezogen, um keine fachlich unbegründeten Annahmen zu treffen.
