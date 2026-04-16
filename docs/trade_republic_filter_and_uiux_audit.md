# Trade-Republic-Filter & UI/UX-Audit (Implementierungsprotokoll)

## Umgesetzte Punkte
- Trade-Republic-Universum als eigener Datenpfad ergänzt (`TradeRepublicUniverseIngestionService`, `TradeRepublicUniverseMatchingService`).
- Fachlicher Status eingeführt:
  - `trade_republic_universe_status` ∈ `IN_UNIVERSE`, `NOT_IN_UNIVERSE`, `UNKNOWN`
  - Keine Behauptung über Live-Handelbarkeit.
- Matching-Regeln:
  - Primär ISIN
  - Fallback `SYMBOL_AND_NAME` nur bei eindeutiger Zuordnung
  - Unsichere Fälle -> `UNKNOWN`.
- MySQL-CLEAN erweitert:
  - neue Felder in `companies` und `insider_trades`
  - Referenztabellen `trade_republic_universe_reference` und `trade_republic_universe_meta`.
- Explorer-UI:
  - neuer Filter „Trade Republic“ mit Optionen „Alle“, „Im Universum“, „Nicht im Universum“, „Unbekannt“
  - aktive Filterchips und Tabellenintegration.
- Unternehmen-Detailseite:
  - TR-Status + Hinweistext zur fachlichen Bedeutung integriert.
- Admin:
  - TR-Datenquelle, Aktualisierung, Instrumentanzahl und Fehlerstatus im Statistikbereich ergänzt.
- Primärnavigation auf 5 Punkte reduziert:
  - Dashboard, Trades, Unternehmen, Admin, Einstellungen.

## Geänderte Dateien
- `src/services/trade_republic_universe_service.py`
- `src/services/import_service.py`
- `src/services/factory.py`
- `src/config/settings.py`
- `src/db/schema.py`
- `src/db/mysql_client.py`
- `src/db/mysql_repository.py`
- `src/services/analysis_service.py`
- `src/ui/pages/explorer_page.py`
- `src/ui/pages/ticker_detail_page.py`
- `src/ui/pages/admin_page.py`
- `src/ui/components/status_badges.py`
- `streamlit_app.py`
- `tests/test_trade_republic_universe.py`

## Architekturentscheidungen
- TR-Referenzdaten sind sauber getrennt vom FMP-Flow als eigener Referenzdienst.
- Matching läuft defensiv und degradiert bei Fehlern auf `UNKNOWN`.
- RAW-Store (Mongo) bleibt unangetastet; CLEAN-Store (MySQL) trägt die fachlichen TR-Felder.
- Refresh ist entkoppelt vom UI-Rendering und wird importseitig „stale-aware“ ausgeführt.

## Fachdefinition TR-Filter
- `IN_UNIVERSE`: Wertpapier ist im offiziellen TR-Universum enthalten.
- `NOT_IN_UNIVERSE`: Wertpapier ist nach aktuellem Referenzsnapshot nicht enthalten.
- `UNKNOWN`: nicht eindeutig zuordenbar oder Referenzdaten nicht belastbar verfügbar.

## Bekannte Grenzen
- Parser erwartet derzeit CSV-Quelle; wenn der offizielle Endpunkt ein anderes Format liefert, bleibt Status defensiv `UNKNOWN`.
- Ohne erreichbare TR-Quelle erfolgt kein harter Ausfall der App.

## Refresh-Mechanik
- URL + TTL sind über ENV konfigurierbar (`TRADE_REPUBLIC_UNIVERSE_URL`, `TRADE_REPUBLIC_REFRESH_TTL_HOURS`).
- Bei stalen Daten wird ein Snapshot geladen, gehasht und in MySQL gespeichert.
- Metadaten (`trade_republic_universe_meta`) enthalten letzten Stand und Fehlerstatus.

## UI/UX-Audit: Behobene Verstöße
- Primärnavigation von 6 auf 5 Hauptpunkte reduziert.
- Trade-Republic-Status textlich sichtbar gemacht (nicht nur Farbe).
- Filterzustand transparenter via Chips + konsistente Tabellenausgabe.

## Bewusst nicht geändert
- Vollständiger visueller Rebuild aller Seiten wurde nicht durchgeführt, um bestehende Fachlogik und Tests nicht zu destabilisieren.
- Methodik-Inhalte wurden nicht gelöscht, sondern nur aus der Primärnavigation entfernt.
