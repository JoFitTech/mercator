# Projekt-Scope: FinanzPort Academic

## Zielsetzung
Das Projekt "FinanzPort Academic" dient als interaktive Datenanwendung zur Analyse öffentlich verfügbarer Insider-Trading-Daten im Rahmen des Moduls **Datenbanken 2**. 

## Funktionaler Scope (MVP)
- **Dashboard:** Überblick über KPIs und Datenverteilung.
- **Datenexplorer:** Interaktive Filter- und Tabellenansicht.
- **Ticker-Detailseite:** Tiefere Analyse einzelner Unternehmen und deren Transaktionen.
- **Methodik-Seite:** Transparente Darstellung von Datenfluss und Technik.
- **Import-Service:** Automatisierter Abruf von FMP-Daten inkl. Gate-Prüfung und Caching.

## Datenquellen & API
Es werden ausschließlich zwei Endpunkte der Financial Modeling Prep (FMP) API verwendet:
1. `Latest Insider Trading`: Abruf der neuesten Insider-Transaktionen (limit=100).
2. `Company Profile Data`: Anreicherung von Metadaten für relevante Unternehmen.

## Nicht-Ziele (Out of Scope)
- Keine Broker-Anbindung oder Trading-Funktionalität.
- Kein Login-/Rollenmodell.
- Keine Realtime-Daten (Feed-Polling max. 1x pro Stunde).
- Keine Mail-Automation oder Benachrichtigungen.
- Keine Social- oder Community-Features.

## Technische Leitplanken
- **Zwei-Datenbank-Architektur:** MongoDB (Rohdaten) + MySQL (strukturierte Daten).
- **Technologien:** Python, Streamlit, Pandas, MySQL, MongoDB, Pytest.
- **Sprache:** UI/Docs in Deutsch, Code/Kommentare in Englisch.
