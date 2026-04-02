# Architektur

## Bausteine
- **Config:** zentrale App-/FMP-/DB-Konfiguration in `src/config/settings.py`.
- **Data Source:** `FmpApiClient` kapselt ausschließlich die zwei freigegebenen FMP-Endpunkte.
- **Preprocessing:** Normalisierung, Typkonvertierung, Dedupe-Key, lokale Gate-Prüfung.
- **MongoDB:** `insider_trades_raw` und `companies` für Rohdaten und Profilcache.
- **MySQL:** `insider_trades` und `companies` für bereinigte, analysierbare Zieldaten.
- **Services:**
  - `ImportService` für Feed-Lauf und Profilnachladung
  - `DashboardService` für KPI-/Chartdaten
  - `AnalysisService` für Explorer und Ticker-Detail
- **UI:** Streamlit mit `st.navigation` und getrennten Seitenmodulen.

## Datenfluss
1. Feed-Abruf über `/insider-trading/latest`.
2. Normalisierung + Deduplizierung + Gate-Evaluierung.
3. Rohpersistenz in MongoDB.
4. Bereinigte Trades in MySQL.
5. Profilabruf über `/profile` nur für Gate-Pass und nur bei abgelaufenem Cache.
6. Streamlit nutzt ausschließlich Services für Lesezugriffe.
