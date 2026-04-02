# Architekturüberblick

## Datenquelle
Ein öffentlich verfügbarer Datensatz (z. B. Insider-Trade-Daten als CSV) wird lokal abgelegt und über den `DatasetLoader` eingelesen.

## Pandas-Verarbeitung
Rohdaten durchlaufen eine erste Bereinigung:
1. leere Zeilen entfernen,
2. Spaltennamen vereinheitlichen,
3. Feldnormalisierung und Typkonvertierung.

## MongoDB für Rohdaten
Die unveränderten Rohdatensätze werden in MongoDB persistiert, um den Ursprungszustand revisionsnah zu erhalten.

## MySQL für bereinigte Daten
Bereinigte und analysierbare Daten werden in MySQL abgelegt, damit KPI-Abfragen und Auswertungen strukturiert möglich sind.

## Streamlit als Analyseoberfläche
Die App stellt Dashboard, Explorer, Ticker-Details und Methodik als Seiten bereit.
