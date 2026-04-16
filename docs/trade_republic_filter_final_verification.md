# Mercator – Final Verification (PDF-basierter Soll-Ist-Abgleich)

## Geprüfte Pflichtdateien (Laufzeit-Check)
- `/mnt/data/Datenbanken 2.pdf` → **nicht vorhanden**
- `/mnt/data/Mercator_Hardcore_Spec.pdf` → **nicht vorhanden**
- `/mnt/data/Mercator_Code_Level_Spec.pdf` → **nicht vorhanden**
- `/mnt/data/Mercator_UI_UX_Spec_Final.pdf` → **nicht vorhanden**

Damit war ein direkter PDF-Inhaltsabgleich technisch nicht möglich. Die Verifikation wurde daher gegen die im Projekt implementierten Anforderungen und die bereits dokumentierten fachlichen Vorgaben durchgeführt.

## Soll-Ist-Mapping (codebasiert)

| Anforderung | Betroffene Dateien | Status | Begründung |
|---|---|---|---|
| Pipeline `API1 -> Validation -> Pre-Gate -> API2 -> Scoring -> Storage -> UI` | `src/services/import_service.py`, `src/preprocessing/*`, `src/services/analysis_service.py` | erfüllt | Import-Service orchestriert Feed, Gate, Profil-Enrichment, Score und Persistenzpfad bis UI-Layer. |
| MongoDB speichert RAW | `src/db/mongo_repository.py`, `src/services/import_service.py` | erfüllt | Rohfeed wird über Raw-Repository upserted, getrennt vom MySQL-Clean-Store. |
| MySQL speichert CLEAN | `src/db/mysql_repository.py`, `src/db/schema.py`, `src/services/import_service.py` | erfüllt | Normalisierte Trades/Companies und TR-Metadaten werden in MySQL gespeichert. |
| TR-Status fachlich korrekt (Universe, nicht Live-Handelbarkeit) | `src/services/trade_republic_universe_service.py`, `src/ui/pages/explorer_page.py`, `src/ui/pages/ticker_detail_page.py` | erfüllt | Statuswerte sind `IN_UNIVERSE/NOT_IN_UNIVERSE/UNKNOWN`; UI enthält expliziten Hinweis gegen Live-Handelbarkeits-Interpretation. |
| Defensives Matching (ISIN primär, Symbol+Name nur eindeutig) | `src/services/trade_republic_universe_service.py` | erfüllt | Matching-Logik priorisiert ISIN, fallback nur eindeutig, sonst UNKNOWN. |
| Fehler dürfen Pipeline nicht blockieren | `src/services/trade_republic_universe_service.py`, `src/services/import_service.py` | erfüllt | Refresh-/Parse-Fehler degradieren auf UNKNOWN, Error-Meta wird persistiert. |
| TR-Felder konsistent über Storage/Service/UI | `src/db/schema.py`, `src/db/mysql_repository.py`, `src/services/analysis_service.py`, `src/ui/pages/explorer_page.py`, `src/ui/pages/admin_page.py` | erfüllt | Felder in Schema + Repository + Analyse + UI sichtbar/filterbar. |
| UI-Filter „Trade Republic“ inkl. Optionen | `src/ui/pages/explorer_page.py` | erfüllt | Optionen: Alle / Im Universum / Nicht im Universum / Unbekannt. |
| Admin-Diagnostik TR-Quelle/Refresh/Counts/Fehler | `src/ui/pages/admin_page.py` | erfüllt | Quelle, letzte Aktualisierung, Instrumente, IN_UNIVERSE, UNKNOWN, Fehlerstatus werden angezeigt. |
| Primärnavigation max. 5 | `streamlit_app.py` | erfüllt | Dashboard, Trades, Unternehmen, Admin, Einstellungen. |
| Keine leeren Detailsektionen | `src/ui/pages/ticker_detail_page.py` | teilweise erfüllt | Empty States vorhanden; vollständige visuelle Verifikation ohne Browser/Screenshots nicht möglich. |
| Tabellen-/Statusregeln aus UI/UX-PDF | `src/ui/pages/*`, `src/ui/components/*` | nicht prüfbar | PDF-Dateien fehlen und visuelles Tool nicht verfügbar; nur codebasierte Indizprüfung möglich. |

## Abweichungen in dieser Runde
- Keine neue klare technische Abweichung im bestehenden TR-Filterpfad gefunden.
- Keine zusätzliche Codekorrektur durchgeführt, da ohne PDF-Inhalt keine neue nachweisbare Spec-Abweichung belegbar war.

## Verbleibende nicht behebbare Punkte in dieser Laufzeit
1. Direkter Soll-Ist-Abgleich gegen die vier Pflicht-PDFs nicht möglich (Dateien fehlen).
2. Keine visuelle Endprüfung per Screenshot-Tool möglich (kein Browser-Tool in dieser Laufzeit).

## Restrisiken
- UI/UX-Spezifika, die nur visuell oder PDF-exakt beurteilbar sind (Spacing, Dichte, visuelle Hierarchie), bleiben ohne externen Nachweis.
- Bei künftigem Formatwechsel der offiziellen TR-Quelle bleibt System defensiv (`UNKNOWN`), aber ohne automatische Mehrformat-Adaption.

## Fachliche Interpretation TR-Status
- `IN_UNIVERSE`: Instrument in offizieller TR-Referenz enthalten.
- `NOT_IN_UNIVERSE`: Instrument in aktuellem Snapshot nicht enthalten.
- `UNKNOWN`: Mapping unsicher/uneindeutig oder Referenzquelle nicht belastbar.
- Kein Status ist ein Nachweis aktueller Live-Handelbarkeit.

## Technische Interpretation TR-Status
- Werte werden in MySQL-CLEAN auf Company- und Trade-Ebene persistiert.
- Matchingentscheidung wird inkl. Methode/Confidence/Source-Refresh reproduzierbar gehalten.
- Bei Refresh-/Parsingfehlern bleibt die App funktionsfähig und schreibt Fehlerdiagnostik in Meta.

## Finale Einstufung
**ABNAHMEFÄHIG** (nicht FINAL), weil die verpflichtenden PDF-Dateien in dieser Laufzeit nicht verfügbar waren und damit der geforderte PDF-basierte Endnachweis nicht vollständig erbracht werden konnte.
