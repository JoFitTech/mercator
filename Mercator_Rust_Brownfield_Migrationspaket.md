# Mercator als Rust-Lernprojekt

## Brownfield-Migrationspaket und Codex-Übergabe

Stand: 18. Juli 2026  
Repository: `JoFitTech/mercator`  
Untersuchter Stand: `main` bei Commit `8038d7a01f26553884297832db5998fedb7acccf`

## 1. Ergebnis

Mercator sollte nicht neu geschrieben werden. Die belastbare Zielrichtung ist eine inkrementelle Brownfield-Migration im bestehenden Repository.

Der erste Migrationsabschnitt bleibt bewusst klein:

1. Den Python-Bestand als verlässliche Referenz reparieren.
2. Einen reinen Rust-Domain-Core ohne I/O anlegen.
3. Zuerst nur die Transaktionscode-Klassifikation portieren.
4. Python und Rust mit denselben Fixtures vergleichen.
5. Erst danach Validation, Gates, Akkumulation und das tatsächlich verwendete Scoring einzeln migrieren.
6. Die Rust-Anbindung später über einen getrennten PyO3-Adapter im Shadow Mode einführen.

Streamlit, FMP-Orchestrierung, MySQL und MongoDB bleiben in dieser ersten Stufe unverändert. Das schützt die funktionierende Anwendung und macht jeden fachlichen Schritt vergleichbar.

Der wichtigste Vorbehalt ist die Referenz-Baseline: Der derzeitige CI-nahe Testlauf ist nicht vollständig grün. Von 449 Tests bestehen 444, fünf schlagen fehl. Diese Abweichungen müssen vor dem ersten produktiven Rust-Aufruf bereinigt werden.

## 2. Verbindliche Quellenhierarchie

Bei Widersprüchen gilt diese Reihenfolge:

1. Die aktuelle ausdrückliche Entscheidung des Projekteigentümers
2. Der tatsächlich ausgeführte Code und die bewusst bestätigten Verträge auf `main`
3. `Mercator_FMP_API_Spec_v2_Final_Project.pdf`
4. Ältere Hardcore-, Code-Level- und UI-Spezifikationen
5. Forschungsunterlagen als fachlicher Hintergrund

Diese Priorität ist notwendig, weil ältere Unterlagen teilweise Zielzustände beschreiben, die im aktuellen Laufzeitpfad nicht umgesetzt sind. Eine PDF-Regel darf deshalb nicht stillschweigend als aktuelles Verhalten behandelt werden.

## 3. Belegte Ausgangslage

### 3.1 Repository

| Merkmal | Befund |
|---|---|
| Repository | `JoFitTech/mercator` |
| Default Branch | `main` |
| Referenz-Commit | `8038d7a01f26553884297832db5998fedb7acccf` |
| Python-Quellcode | 95 Dateien, rund 18.733 Zeilen unter `src/` |
| Tests | 72 Python-Testdateien, rund 11.438 Zeilen |
| Test-Collection | 449 Tests ohne E2E |
| Anwendung | Python, Streamlit, Pandas |
| Datenbanken | MySQL 8.4 und MongoDB 7 |
| Container | Python 3.11, Docker Compose |
| Rust auf `main` | Kein Cargo-Workspace und keine Rust-Crates |
| Spec Kit auf `main` | Keine `.specify/`-Struktur |
| CI | Python-Tests unter Ubuntu mit Python 3.11, noch kein Rust-Job |

### 3.2 Relevante Remote-Branches

| Branch | Befund | Empfehlung |
|---|---|---|
| `origin/docs/rust-learning-plan` | Vier reine Dokumentations-Commits vor `main` | Als dokumentarische Basis verwenden, vorher fachlich korrigieren |
| `origin/feature/stocklens-brownfield` | Sieben Commits vor `main`, enthält Spec-Kit-Gerüst und eine andere Stocklens-Funktion | Nicht mergen und nicht als Migrationsbasis verwenden |
| `origin/codex/p1-p2-performance-foundations` | Weit hinter `main` | Nicht als Basis verwenden |

Der Branch `docs/rust-learning-plan` enthält bereits `AGENTS.md`, `docs/RUST_MIGRATION_PLAN.md` und `docs/RUST_LEARNING_LOG.md`. Er ist eine gute Grundlage, aber noch nicht unverändert freigabefähig:

- Kommentare und Rust-Doc-Comments sollen Englisch sein. Nur die Lern- und Fortschrittsdokumentation bleibt Deutsch.
- Das Dokument schlägt `Decimal` vor, während die Python-Referenz mit binären Gleitkommazahlen rechnet. Der Zahlentyp benötigt vor der numerischen Portierung einen ADR.
- Als Scoring-Referenz muss der aktuelle Aufrufpfad `ScoringService -> buy_engine.score_trade` genannt werden.
- Akkumulation ist derzeit nicht Teil der produktiven Import-Orchestrierung. Das muss als Ist-Abweichung dokumentiert werden.

### 3.3 Aktueller Laufzeitpfad

Der heute ausgeführte Pfad ist vereinfacht:

```text
FMP API 1
  -> Normalisierung und Validierung
  -> Gates
  -> MongoDB Raw-Bereich und MySQL Clean-Bereich
  -> selektives Profile-Enrichment über API 2
  -> historische Kurse über API 3
  -> ScoringService -> buy_engine.score_trade
  -> Streamlit
```

Wichtig: Die lokale Akkumulation ist zwar implementiert und in der UI beziehungsweise Analyse nutzbar, aber nicht wie in der finalen FMP-Spezifikation vor API 2 in die aktuelle Import-Pipeline geschaltet.

### 3.4 Aktueller Testbefund

Ausgeführt wurde der CI-nahe Testlauf in einer isolierten Python-Umgebung:

```bash
env \
  FMP_API_KEY=test_key \
  MYSQL_ACTIVE_TARGET=local \
  MONGO_ACTIVE_TARGET=local \
  MERCATOR_UI_TEST_MODE=true \
  MERCATOR_DISABLE_IMPORT=true \
  python -m pytest tests --ignore=tests/e2e -q
```

Ergebnis:

```text
449 collected
444 passed
5 failed
1 warning
```

| Fehlergruppe | Ursache | Erforderliche Korrektur |
|---|---|---|
| Sell-Warning-Scoring | Fester Filing-Termin wird gegen die reale aktuelle Uhrzeit bewertet | Explizite `as_of`-Zeit beziehungsweise Clock-Injektion einführen |
| API-2-Gate-Test | Mock-Datensätze erfüllen den inzwischen erweiterten Validierungsvertrag nicht | Fixtures an den aktuellen Vertrag anpassen, nicht die Validierung abschwächen |
| Persistenz bei Enrichment-Fehler | Mock-Datensatz enthält keinen inzwischen nötigen Dedupe-Key | Fixture und Vertrag explizit machen |
| Zwei Ticker-Tests | Alter Test erwartet nur Trade-Symbole, neuer Code und neuerer Test erwarten Trade- plus Company-Symbole | Aktuellen Produktvertrag bestätigen und den veralteten Test korrigieren |
| Pytest-Warnung | `pytest.ini` nutzt Timeout-Konfiguration, der CI-Installationspfad installiert das Plugin nicht | Dev-Abhängigkeiten im CI-Pfad vollständig installieren |

Ziel von Phase 0 ist ein grüner Referenzlauf. Tests dürfen nicht gelöscht, übersprungen oder inhaltlich abgeschwächt werden, um dieses Ziel zu erreichen.

### 3.5 Externe Schnittstellen und Persistenzinventar

Im aktuellen Code sind folgende FMP-Pfade nachweisbar:

- `/insider-trading/latest`
- `/profile`
- `/profile-cik`
- `/search-cik`
- `/insider-trading/search`
- `/insider-trading/reporting-name`
- `/historical-price-eod/full`
- optionale Statistik- und Screener-Aufrufe
- `/search-exchange-variants`, derzeit ohne nachgewiesenen Runtime-Aufruf

Die fehlende Runtime-Referenz ist ein bewusstes Nicht-Portierungskriterium. Ein vorhandener Helper allein rechtfertigt keinen neuen Rust-Adapter.

Die aktuelle MySQL-Struktur umfasst unter anderem:

- `companies`
- `insider_trades`
- `company_trade_stats`
- `market_signal_cache`
- `app_data_state`
- `trade_republic_universe_reference`
- `trade_republic_universe_meta`
- `app_filter_settings`
- `app_runtime_preferences`
- `app_sync_state`
- `app_api_usage`

MongoDB verwendet die Collections `insider_trades_raw`, `companies` und `app_settings`. Der Raw-Trade-Pfad besitzt einen Dedupe-Vertrag. Dieser bestehende Datenbestand bleibt während der Domain-Migration unangetastet.

Docker Compose bindet Anwendung, MySQL und MongoDB derzeit an `127.0.0.1`. Gleichzeitig enthält das Projekt noch Cloudflared-Download und Public-Share-Code. Dessen Entfernung ist eine sinnvolle spätere Hardening-Aufgabe, aber kein Bestandteil von `001-rust-foundation`.

## 4. Fachliche Ist-Verträge und Drift

### 4.1 Transaktionscode-Klassifikation

Die normative aktuelle Implementierung liegt in `src/services/transaction_code_classifier.py`.

| Codes | Aktuelle Klasse |
|---|---|
| `P` | `CORE_BUY` |
| `S` | `CORE_SELL` |
| `I`, `L` | `SECONDARY_SIGNAL` |
| `J`, `V` | `MANUAL_REVIEW` |
| `A`, `C`, `D`, `E`, `F`, `G`, `H`, `K`, `M`, `O`, `U`, `W`, `X`, `Z` | `EXCLUDE_FROM_CORE` |
| Leer oder unbekannt | `MANUAL_REVIEW`, Code `UNKNOWN` beziehungsweise erstes normalisiertes Zeichen |

Der Parser akzeptiert auch Werte wie `P-Purchase`, indem nach Trim und Großschreibung das erste Zeichen verwendet wird. Dieses Verhalten muss im ersten Rust-Meilenstein exakt erhalten bleiben.

### 4.2 Gates

Der aktuelle Standardvertrag umfasst unter anderem:

- Mindest-Trade-Value 100.000 USD
- Form Type 4
- ausschließlich Stocks und ETFs
- Filing Age über 45 Tagen als Reject
- Filing Age über 21 Tagen als Pending beziehungsweise Watchlist
- lokale Transaktionscode-Matrix

Es gibt mehrere überlappende Konfigurationsquellen. Das Feld `required_validation_status` ist nicht als allgemeiner Gate-Mechanismus umgesetzt. Die Rust-Migration darf diese Drift nicht beiläufig bereinigen. Zuerst wird das heutige Verhalten festgehalten. Eine fachliche Verbesserung erfolgt später in einem eigenen ADR und mit getrennten Tests.

### 4.3 Scoring

Portiert wird ausschließlich das aktuelle Modell in:

```text
src/services/scoring_service.py
  -> src/services/buy_engine.py::score_trade
```

Der unreferenzierte Pfad `src/domain_rules.py::compute_discrete_score` ist keine Portierungsquelle.

Das aktuelle Buy-Engine-Modell kombiniert:

- Core Insider Score
- Investability Score
- Execution Score
- Trade-Republic Score

Die Scoreklassen sind aktuell:

| Klasse | Schwelle |
|---|---:|
| A | mindestens 85 |
| B | mindestens 70 |
| C | mindestens 55 |
| D | mindestens 40 |
| E | darunter |

Trade Republic ist kein hartes Gate. Ein `NOT_FOUND`-Status begrenzt die Entscheidung derzeit auf Watchlist. Diese Semantik wird entweder exakt portiert oder vor der Portierung ausdrücklich geändert. Sie darf nicht unbemerkt verschwinden.

Daneben existiert eine getrennte `ScoreGatePolicy` mit PASS ab 90, HOLD ab 70 und FAIL darunter. Diese Schwellen sind nicht identisch mit den Scoreklassen und müssen im Traceability-Dokument getrennt geführt werden.

### 4.4 Akkumulation

Die aktuelle Implementierung:

- gruppiert nach Symbol zum Trade-Zeitpunkt, Reporting Name und Richtung
- trennt Acquisition und Disposition
- startet eine neue Gruppe erst bei einer Lücke größer als das konfigurierte Fenster von drei Tagen
- verwendet damit eine verkettete Lückenlogik
- schließt ungültige Preise aus
- berechnet den gewichteten Preis als Gesamtwert geteilt durch Gesamtmenge

Beispiel für die verkettete Logik: Tage 1, 3 und 5 bilden eine Gruppe, obwohl die Gesamtspanne mehr als drei Tage beträgt, weil keine einzelne Lücke größer als drei Tage ist.

Bekannte Unklarheiten:

- README und Code unterscheiden sich bei CIK, Name und Security Kind als Gruppenschlüssel.
- Die Multi-Insider-Metrik ist nicht sauber auf ein rollierendes Drei-Tage-Fenster begrenzt.
- Die FMP-Spezifikation ordnet Akkumulation vor API 2 ein, der aktuelle Import-Service tut dies nicht.

Diese Punkte benötigen vor `003-rust-accumulation` einen eigenen ADR.

### 4.5 Instrument-Normalisierung

Die Gate- und Cleaning-Schicht verwendet `STOCK` und `ETF`. Die Investability-Bewertung erwartet dagegen unter anderem `OPERATING_COMPANY_EQUITY`, `ETF`, `ADR` und `FUND`.

Damit kann ein normalisiertes Common Stock im aktuellen Laufzeitpfad andere Punkte erhalten als in Tests, die `OPERATING_COMPANY_EQUITY` verwenden. Das ist ein bestätigter Driftpunkt und muss vor der Scoring-Portierung entschieden werden.

### 4.6 Raw-Store

MongoDB wird konzeptionell als Raw Store beschrieben. Der Import-Service speichert derzeit normalisierte Records mit eingebettetem `raw_payload`, nicht ausschließlich die unveränderte API-Antwort. Vor einer Storage-Migration muss definiert werden, ob „raw“ die vollständige unveränderte Antwort, ein normalisiertes Envelope oder beides bedeutet.

## 5. Zielarchitektur in Stufen

### Stufe A: Rust-Domain-Core im bestehenden System

```text
Streamlit und Python-Orchestrierung
  -> Python-Referenz oder Rust-Adapter
  -> reiner Rust-Domain-Core
  -> bestehendes MySQL und MongoDB
```

Der Domain-Core kennt kein Python, keine Datenbank, kein HTTP und keine UI. Er enthält nur deterministische Datentypen und Fachfunktionen.

### Stufe B: Shadow Mode und kontrollierter Cutover

```text
Python-Eingabe
  -> Python-Ergebnis A
  -> Rust-Ergebnis B
  -> strukturierter Paritätsvergleich
  -> zunächst weiterhin Python-Schreibpfad
```

Erst nach dokumentierter Parität wird Rust pro Komponente über einen Feature-Schalter zum primären Rechenpfad. Ein getesteter Python-Fallback bleibt vorerst erhalten.

### Stufe C: Rust-Backend und späterer Datenbankwechsel

Nach vollständiger Domain-Parität können FMP-Client, Import-Worker, Repositories und eine Axum-API einzeln folgen. MySQL und MongoDB bleiben bis dahin unverändert. Ein späterer Wechsel zu PostgreSQL wird als eigene Datenmigration mit Shadow Reads, Backfill, Checksummen und Rollback durchgeführt.

### Stufe D: Optionale UI-Ablösung

Streamlit wird erst ersetzt, wenn Backend und Datenpfad stabil sind. Das langfristige Ziel kann Axum mit Askama und HTMX sein. Diese UI-Arbeit gehört nicht in die ersten Rust-Features.

Für den Betrieb gelten weiterhin:

- keine Orderausführung
- kein LLM oder Agent im Produkt
- kein öffentlich freigegebener Zugriff
- Betrieb auf privater Infrastruktur über LAN beziehungsweise VPN

## 6. Empfohlener Rust-Workspace

```text
rust/
├── Cargo.toml
├── rust-toolchain.toml
└── crates/
    ├── mercator-domain/       # erster und reiner Fachkern
    ├── mercator-python/       # späterer PyO3-Adapter
    ├── mercator-application/  # spätere Use Cases und Ports
    ├── mercator-fmp/          # späterer HTTP-Adapter
    ├── mercator-storage/      # spätere DB-Adapter
    ├── mercator-api/          # spätere Axum-API
    └── mercator-worker/       # späterer Import-Worker
```

Im ersten Rust-PR wird nur `mercator-domain` angelegt. `mercator-python` folgt erst, wenn mindestens eine reine Domain-Funktion mit Golden-Master-Tests abgesichert ist.

Technische Grundsätze:

- virtueller Cargo-Workspace mit `resolver = "3"`
- Rust Edition 2024
- explizit gepinnte und dokumentierte stabile Toolchain zum Zeitpunkt der Umsetzung
- ein gemeinsames `Cargo.lock`
- `unsafe_code = "forbid"` auf Workspace-Ebene, sofern keine begründete Ausnahme entsteht
- `cargo fmt --check`, `cargo clippy --workspace --all-targets --all-features -- -D warnings` und `cargo test --workspace`
- keine PyO3-, Tokio-, Reqwest-, SQLx- oder MongoDB-Abhängigkeit in `mercator-domain`
- Code, Bezeichner, Kommentare und Doc-Comments auf Englisch
- Lernlog und wöchentlicher Fortschritt auf Deutsch

Für die spätere Python-Anbindung ist ein separates `mercator-python`-Crate mit PyO3 und Maturin sinnvoll. Die Trennung verhindert, dass Python-Typen in die Fachlogik durchsickern. Maturin unterstützt einen gemischten Python/Rust-Aufbau und einen privaten Submodulnamen wie `mercator._mercator_core`.

## 7. Zahlentyp und Zeitsemantik

Vor Gates, Akkumulation und Scoring sind zwei ADRs Pflicht.

### 7.1 Zahlentyp

Die Python-Referenz verwendet `float`. Ein sofortiger Wechsel auf Dezimalarithmetik wäre fachlich möglicherweise sinnvoll, wäre aber keine reine Portierung.

Empfehlung:

1. Für die erste Verhaltensparität die heutige `float`-Semantik explizit als Rust `f64` nachbilden.
2. Vergleichstoleranzen und Reihenfolge der Operationen dokumentieren.
3. Geldbeträge und Rundungsregeln in einem separaten späteren ADR auf `Decimal` beziehungsweise feste Minor Units prüfen.
4. Eine solche Umstellung als fachliche Änderung mit eigenen Migrationstests behandeln.

### 7.2 Zeit

Kein Domain-Service darf direkt die Systemzeit lesen. Zeitabhängige Funktionen erhalten ein explizites `as_of`-Datum oder eine Clock-Abstraktion. Golden-Master-Fixtures enthalten den Bewertungszeitpunkt. So bleiben Tests unabhängig vom Ausführungsdatum.

## 8. Spec-Kit-Vorbereitung

Auf `main` ist Spec Kit nicht initialisiert. Der fremde Stocklens-Branch enthält ein Gerüst der Version `0.12.5.dev0`. Laut offizieller Release-Seite ist am 18. Juli 2026 `v0.13.0` aktuell. Das alte Gerüst darf nicht blind kopiert werden.

Vor der Initialisierung im bestehenden Repository:

```text
specify --version
specify self check
specify self upgrade --dry-run
specify init --help
```

Danach wird die zum geprüften CLI-Stand passende In-Place-Initialisierung mit Codex-Integration gewählt. Die tatsächlichen Flags werden aus `specify init --help` übernommen. Ein erneutes Greenfield-Projekt oder ein separater Projektordner ist nicht erlaubt.

Die Constitution sollte mindestens enthalten:

1. Brownfield und gleiche Git-Historie
2. Verhaltensparität vor Verbesserung
3. Python als Test-Oracle und temporärer Fallback
4. Reiner Domain-Core ohne I/O
5. Explizite Zeit- und Zahlensemantik
6. Unit-Test für jede fachliche Berechnung
7. Kein Abschwächen bestehender Tests
8. Kleine vertikale Migrationseinheiten und messbare Cutover-Kriterien
9. Code und Kommentare Englisch, Lernfortschritt Deutsch
10. Keine Orderausführung, kein Produkt-LLM und kein öffentlicher Zugang

## 9. Spec-Kit-Features

| Feature | Scope | Cutover-Kriterium |
|---|---|---|
| `001-rust-foundation` | Python-Baseline, Governance, Cargo-Workspace, Transaktionscode-Klassifikation | Python grün, Rust grün, vollständige Klassifikationsparität |
| `002-rust-validation-gates` | DTOs, Normalisierung, Validation, Gates, explizite Zeit | Golden Master für alle Gate-Grenzen und Fehlerpfade |
| `003-rust-accumulation` | Same-Insider- und Multi-Insider-Akkumulation nach geklärtem ADR | Parität für Fenstergrenzen, Richtungen, Gewichtung und Reihenfolge |
| `004-rust-current-scoring` | Nur `ScoringService -> buy_engine.score_trade` | Parität der Komponenten, Klassen, Status, Caps und Ablehnungen |
| `005-python-rust-shadow` | PyO3/Maturin, Batch-API, Feature Flag, Telemetrie und Fallback | Kein ungeklärter Diff im festgelegten Korpus und Lasttest |
| `006-rust-backend-evolution` | FMP, Worker, Storage, Axum, später PostgreSQL und UI-Cutover | Pro Adapter eigener Shadow- und Rollback-Nachweis |

Jedes Feature erhält `spec.md`, `plan.md`, `tasks.md`, Research beziehungsweise ADR-Verweise und eine aktualisierte Traceability-Matrix.

## 10. Exakter Umfang von `001-rust-foundation`

### Phase 0: Python-Referenz stabilisieren

1. Die fünf aktuellen Testfehler reproduzieren und dokumentieren.
2. Systemzeit aus dem Scoring-Vertrag entfernen und einen expliziten Bewertungszeitpunkt einführen.
3. Stale Mocks um aktuell verpflichtende Felder ergänzen.
4. Den Ticker-Optionsvertrag anhand des aktuellen Codes und der UI-Erwartung festlegen. Empfohlener Default ist Trade- plus Company-Symbole, weil dies der neuere Produktpfad ist.
5. `pytest-timeout` im CI-Installationspfad verfügbar machen.
6. Den vollständigen Non-E2E-Lauf auf grün bringen.
7. Repräsentative, anonymisierte oder synthetische JSON-Fixtures unter einer klaren Teststruktur ablegen.

Definition of Done für Phase 0:

```text
449/449 oder die nach nachvollziehbaren neuen Tests höhere Anzahl besteht.
Keine Tests sind gelöscht, übersprungen oder in ihren fachlichen Aussagen abgeschwächt.
Zeitabhängige Ergebnisse verwenden einen expliziten Bewertungszeitpunkt.
```

### Phase 1: Rust-Grundlage und Klassifikation

1. Virtuellen Workspace unter `rust/` anlegen.
2. Nur das Crate `mercator-domain` anlegen.
3. Die Transaktionscode-Domain mit typisierten Klassen und explizitem Unknown-Fall modellieren.
4. Das Python-Verhalten inklusive Trim, Case-Normalisierung, `P-Purchase`, leerem Wert und unbekanntem Code exakt portieren.
5. Tabellengetriebene Rust-Unit-Tests für alle bekannten und ausgeschlossenen Codes anlegen.
6. Einen gemeinsamen Fixture-Korpus verwenden oder aus einer neutralen JSON-Datei lesen.
7. Einen Python-Test hinzufügen, der dieselben Fixtures gegen die Python-Referenz prüft.
8. Noch keine PyO3-Anbindung und noch keine Änderung des produktiven Python-Pfads vornehmen.
9. Einen Rust-CI-Job ergänzen.
10. Den deutschen Lernlog mit den tatsächlich gelernten Rust-Konzepten, Fehlern und Entscheidungen aktualisieren.

Definition of Done für Phase 1:

```text
Python-Tests grün
cargo fmt --check grün
cargo clippy --workspace --all-targets --all-features -- -D warnings grün
cargo test --workspace grün
Alle Klassifikations-Fixtures liefern in Python und Rust dieselbe Klasse, denselben normalisierten Code und denselben erklärten Fall.
Keine DB-, HTTP-, Streamlit- oder produktive Importänderung.
```

## 11. Empfohlene Pull-Request-Reihenfolge

1. Dokumentations-PR aus `docs/rust-learning-plan`, nach den Korrekturen aus diesem Dokument
2. Baseline-PR für die fünf Python-Testfehler und deterministische Zeit
3. `001-rust-foundation` mit Cargo-Workspace, Klassifikation und Rust-CI
4. Pro weiterem Spec-Kit-Feature mindestens ein eigener fachlicher PR

Kleine PRs sind hier wichtiger als eine künstlich schnelle Gesamtrewrite. Jede Stufe muss reversibel bleiben.

## 12. Entscheidungsregister

| Thema | Aktueller Befund | Entscheidung für den Start |
|---|---|---|
| Migration | Ältere Ideen enthalten Greenfield-Anteile | Brownfield im selben Repo |
| Python | Funktionierende Anwendung und Referenz | Oracle und Fallback erhalten |
| Erster Rust-Scope | Mehrere mögliche Services | Nur Transaktionscode-Klassifikation nach Baseline |
| Scoring | Mehrere Beschreibungen und ein unreferenzierter Helper | Nur aktueller Buy-Engine-Pfad |
| Akkumulation | Spec und Runtime weichen ab | Vor Portierung ADR, kein stiller Pipeline-Umbau |
| Geldarithmetik | Python `float`, Planentwurf `Decimal` | Zunächst `f64` für Parität, spätere Änderung getrennt |
| Zeit | Implizite Systemzeit | Explizites `as_of` |
| Instrumente | `STOCK` versus `OPERATING_COMPANY_EQUITY` | Vor Scoring ADR und Fixture |
| Ticker-Optionen | Zwei widersprüchliche Tests | Neueren Trade-plus-Company-Vertrag bestätigen |
| Mongo Raw | Normalisierter Record mit `raw_payload` | Vor Storage-Migration präzisieren |
| Datenbanken | Heute MySQL und MongoDB | Zunächst unverändert, PostgreSQL später separat |
| UI | Heute Streamlit | Zunächst unverändert, später optional Askama/HTMX |
| Netzwerkfreigabe | Lokale Bindings, aber vorhandener Cloudflared/Public-Share-Pfad | Separater Hardening-PR nach der Foundation |
| Trade Republic | Score-Cap, kein hartes Gate | Aktuelle Semantik explizit testen |
| API-Umfang | Tote Exchange-Variant-Pfade existieren | Nicht portieren, solange kein Runtime-Nachweis besteht |

## 13. Kopierfertiger Codex-`/plan`-Prompt

Der folgende Prompt ist absichtlich auf `001-rust-foundation` begrenzt. Plan Mode soll erst den konkreten dateibezogenen Ausführungsplan erzeugen und offene Abweichungen sichtbar machen.

```text
/plan

Du arbeitest im bestehenden Repository JoFitTech/mercator. Plane eine inkrementelle Brownfield-Migration zu einem Rust-Lernprojekt. Plane keinen Greenfield-Rewrite und implementiere in diesem Plan-Schritt noch nichts.

Ziel dieses Plans ist ausschließlich das Spec-Kit-Feature 001-rust-foundation:

1. Den aktuellen Python-Bestand als deterministische Referenz auf grün bringen.
2. Einen virtuellen Cargo-Workspace unter rust/ mit genau einem reinen Crate mercator-domain anlegen.
3. Als erste Fachfunktion ausschließlich src/services/transaction_code_classifier.py portieren.
4. Python und Rust mit demselben Fixture-Korpus auf vollständige Parität testen.
5. Rust-Checks in CI ergänzen.
6. Streamlit, FMP-Orchestrierung, MySQL, MongoDB und den produktiven Importpfad unverändert lassen.

Verbindliche Quellpriorität:

1. Diese aktuelle Aufgabenbeschreibung
2. Ausgeführter Code und bewusst bestätigte Tests auf main
3. Mercator_FMP_API_Spec_v2_Final_Project.pdf
4. Ältere Hardcore-, Code-Level- und UI-Spezifikationen
5. Forschungsunterlagen nur als Hintergrund

Validiere zuerst den Repository-Zustand:

- main muss erneut gegen origin/main geprüft werden.
- Dokumentiere den aktuellen Commit und einen schmutzigen Worktree, ohne fremde Änderungen zu überschreiben.
- Prüfe origin/docs/rust-learning-plan. Zum untersuchten Stand lag er genau vier Dokumentations-Commits vor main und ist die bevorzugte Dokumentationsbasis.
- Prüfe origin/feature/stocklens-brownfield nur lesend. Dieser Branch enthält eine andere Stocklens-Funktion und darf weder gemergt noch als Implementierungsbasis verwendet werden.
- Suche nach AGENTS.md, .specify, bestehenden Rust-Dateien und weiteren lokalen Anweisungen.

Reproduziere als Planungsbeleg diesen Non-E2E-Testlauf in einer isolierten Umgebung:

FMP_API_KEY=test_key
MYSQL_ACTIVE_TARGET=local
MONGO_ACTIVE_TARGET=local
MERCATOR_UI_TEST_MODE=true
MERCATOR_DISABLE_IMPORT=true
python -m pytest tests --ignore=tests/e2e -q

Beim untersuchten Stand wurden 449 Tests gesammelt, 444 bestanden und fünf schlugen fehl. Prüfe, ob der Befund noch gilt. Die bekannten Problemgruppen waren:

- zeitabhängiger Sell-Warning-Test durch direkte Systemzeit im Scoring
- veraltete Import-Mocks ohne heute benötigte Validierungs- oder Dedupe-Felder
- widersprüchliche Ticker-Option-Tests
- fehlendes pytest-timeout im CI-Installationspfad

Plane eine Phase 0, die diese Ursachen behebt. Keine Tests löschen, überspringen oder fachlich abschwächen. Zeitabhängige Domainlogik muss ein explizites as_of erhalten. Wenn der aktuelle Befund abweicht, plane anhand der neuen Evidenz und dokumentiere den Unterschied.

Prüfe Spec Kit, bevor du Änderungen planst:

- specify --version
- specify self check
- specify self upgrade --dry-run
- specify init --help

Auf einem fremden Branch lag ein 0.12.5.dev0-Gerüst. Zum 18.07.2026 war laut offizieller Release-Seite v0.13.0 aktuell. Verwende nicht blind das alte Gerüst. Plane eine In-Place-Initialisierung mit der zum Ausführungszeitpunkt geprüften Version und Codex-Integration. Erzeuge kein neues Projektverzeichnis und übernimm keine Stocklens-Spezifikation. Falls Spec Kit im aktuellen Branch bereits sauber initialisiert ist, plane eine Audit- beziehungsweise Upgrade-Strategie statt einer zweiten Initialisierung.

Die Constitution und AGENTS.md müssen diese Regeln festhalten:

- Brownfield im selben Repository und mit derselben Historie
- Verhaltensparität vor fachlicher Verbesserung
- Python bleibt Test-Oracle und temporärer Fallback
- mercator-domain hat kein Python, kein PyO3, kein HTTP, keine Datenbank und keine UI
- jede fachliche Berechnung erhält Unit-Tests
- kein direkter Zugriff auf die Systemzeit in Domainlogik
- Code, Bezeichner, Kommentare und Doc-Comments Englisch
- Lernlog und wöchentlicher Fortschritt Deutsch
- keine Orderausführung, kein Produkt-LLM und kein öffentlicher Zugriff
- keine stillen Verhaltensänderungen

Fachliche Referenz für den ersten Rust-Port:

- P -> CORE_BUY
- S -> CORE_SELL
- I und L -> SECONDARY_SIGNAL
- J und V -> MANUAL_REVIEW
- A, C, D, E, F, G, H, K, M, O, U, W, X und Z -> EXCLUDE_FROM_CORE
- leer oder unbekannt -> MANUAL_REVIEW
- Trim, Großschreibung und Eingaben wie P-Purchase müssen sich wie in Python verhalten

Architektur für 001:

rust/
  Cargo.toml als virtueller Workspace mit resolver = "3"
  rust-toolchain.toml mit zum Implementierungszeitpunkt geprüfter und explizit gepinnter stabiler Toolchain
  crates/mercator-domain/

Nutze Edition 2024. Setze Workspace-Lints sinnvoll streng, nach Möglichkeit unsafe_code = "forbid". Plane diese Prüfungen:

- cargo fmt --check
- cargo clippy --workspace --all-targets --all-features -- -D warnings
- cargo test --workspace
- vollständiger Python-Non-E2E-Testlauf

Noch nicht Teil von 001:

- PyO3 oder Maturin
- Validation und Gates in Rust
- Akkumulation in Rust
- Scoring in Rust
- FMP-Client, API, Worker oder Repositories in Rust
- Datenbankmigration
- Streamlit-Ablösung
- Performanceversprechen oder produktiver Rust-Cutover

Beachte für spätere Features, aber implementiere sie nicht:

- Scoring-Referenz ist ausschließlich src/services/scoring_service.py -> src/services/buy_engine.py::score_trade. src/domain_rules.py::compute_discrete_score ist unreferenziert.
- Akkumulation ist derzeit nicht in der Import-Pipeline vor API 2. Vor ihrer Portierung ist ein ADR nötig.
- Python verwendet float. Ein Wechsel zu Decimal ist eine spätere fachliche Entscheidung. Für die erste numerische Parität wird f64 empfohlen.
- STOCK und OPERATING_COMPANY_EQUITY sind derzeit inkonsistent.
- Trade Republic ist kein hartes Gate. NOT_FOUND wirkt aktuell als Watchlist-Cap.
- Mongo Raw speichert derzeit normalisierte Records mit raw_payload und nicht nur die unveränderte Antwort.

Erzeuge als Antwort einen konkreten Ausführungsplan mit:

1. bestätigtem Ist-Zustand und Abweichungen von den oben genannten Befunden
2. exakter Branch-Strategie
3. dateiweiser Änderungsliste
4. Spec-Kit-Artefakten für 001-rust-foundation
5. separaten Schritten für Python-Baseline und Rust-Foundation
6. Test- und CI-Matrix
7. Risiken, Rollback und Stop-Kriterien
8. Definition of Done
9. expliziter Liste aller nicht in Scope liegenden Punkte

Triff keine stillen Annahmen. Wenn eine Entscheidung die fachlichen Ergebnisse ändern würde, markiere sie als ADR oder Blocker. Der Plan muss klein genug sein, dass Phase 0 und Phase 1 getrennt reviewbar und commitbar bleiben. Plane keinen Push, Merge oder Pull Request ohne separate Freigabe.
```

## 14. Codex-Prompt für die anschließende Umsetzung

`/plan` plant, implementiert aber noch nicht. Nach Prüfung und Freigabe des erzeugten Plans folgt im selben Codex-Chat diese zweite Eingabe:

```text
Setze den freigegebenen Plan jetzt ausschließlich für 001-rust-foundation um.

Arbeite testgetrieben und in dieser Reihenfolge:

1. Repository-, Remote- und Worktree-Zustand erneut prüfen.
2. Keine fremden Änderungen überschreiben.
3. Die vereinbarte Dokumentationsbasis verwenden und ihre bekannten fachlichen Fehler korrigieren.
4. Spec Kit nur nach Versions- und In-Place-Prüfung initialisieren oder aktualisieren.
5. Zuerst Phase 0 vollständig abschließen und den Python-Non-E2E-Lauf grün machen.
6. Erst danach den reinen Cargo-Workspace und mercator-domain anlegen.
7. Nur die Transaktionscode-Klassifikation portieren.
8. Gemeinsame Fixtures und Paritätstests ergänzen.
9. Python- und Rust-CI-Prüfungen ausführen.
10. Den deutschen Lernlog und die Traceability aktualisieren.

Halte dich exakt an Scope, ADRs, AGENTS.md und Constitution. Führe keine DB-, API-, UI-, PyO3-, Akkumulations- oder Scoring-Migration aus. Ändere keine fachliche Regel stillschweigend. Wenn Phase 0 nicht ohne eine neue Produktentscheidung grün werden kann, stoppe vor dem Rust-Code und berichte den Blocker mit konkreter Evidenz.

Am Ende liefere:

- Zusammenfassung der Änderungen
- vollständige Liste geänderter Dateien
- ausgeführte Befehle und Testergebnisse
- verbleibende Risiken und bewusste Nicht-Änderungen
- Diff- und Statusübersicht

Erstelle keinen Commit, Push, Merge oder Pull Request, solange ich das nicht separat beauftrage.
```

## 15. Wöchentlicher Lernpfad

Die Wochen sind Lernabschnitte, keine verbindlichen Kalenderzusagen.

| Lernabschnitt | Ergebnis | Rust-Schwerpunkt |
|---|---|---|
| 0 | Python-Oracle grün und deterministisch | Grenzverträge verstehen |
| 1 | Transaction Classifier | Enums, Pattern Matching, Module, Tests |
| 2 | Validation und Gates | `Result`, Fehler-Enums, Newtypes, Zeit |
| 3 | Akkumulation | Iteratoren, Ownership, Sortierung, Property Tests |
| 4 | Aktuelles Scoring | Komposition, numerische Semantik, Exhaustiveness |
| 5 | PyO3 Shadow Mode | FFI-Grenzen, Batch-DTOs, Fehlerabbildung |
| 6 | Messung und Cutover | Benchmarks, Telemetrie, Fallback und Rollback |

Nach jedem Abschnitt wird `docs/RUST_LEARNING_LOG.md` aktualisiert mit:

- Ziel
- neuem Rust-Konzept
- Bezug zur Python-Referenz
- Fehlern und Ursachen
- Tests und Messwerten
- offenen Fragen
- nächstem kleinen Schritt

## 16. Quellen

### Projekt und Anhänge

- Repository-Stand: [JoFitTech/mercator bei Commit 8038d7a](https://github.com/JoFitTech/mercator/tree/8038d7a01f26553884297832db5998fedb7acccf)
- `Mercator_FMP_API_Spec_v2_Final_Project.pdf`, primäre Projektspezifikation für API-Sequenz, lokale Taxonomie, Stocks und ETFs, 500-Tage-Lookback und Raw/Clean-Ziel
- `Mercator_Hardcore_Spec.pdf` und `Mercator_Code_Level_Spec.pdf`, ältere Architektur- und Implementierungsbeschreibung
- `Mercator_UI_UX_Spec_Final.pdf`, Streamlit- und Darstellungsvertrag
- `Deepresearch - Forschungsgrundlage für die Projektarbeit zu Mercator.pdf` und `Agent - Forschungsgrundlage Mercator Projektarbeit.pdf`, Forschungs- und Evidenzsammlungen
- `Decoding Inside Information_Mercator.pdf`, fachlicher Hintergrund zur Unterscheidung von Insider-Handelsmustern. Kein Quellvertrag für Mercator-Schwellenwerte
- `Advancing Analytical Database Systems_Mercator.pdf` und `Data Science – Analytics_Mercator.pdf`, Datenbank- und Analysehintergrund. Kein Quellvertrag für den ersten Rust-Port
- DHBW-Unterlagen und `Datenbanken 2.pdf`, formaler beziehungsweise didaktischer Kontext des ursprünglichen Python-, Streamlit-, MySQL- und MongoDB-Projekts

### Offizielle technische Quellen

- [Codex Plan Mode](https://developers.openai.com/codex/developer-commands#switch-to-plan-mode-with-plan)
- [Codex Best Practices für Plan Mode](https://developers.openai.com/codex/learn/best-practices#plan-first-for-difficult-tasks)
- [Codex AGENTS.md](https://developers.openai.com/codex/agent-configuration/agents-md)
- [Codex Execution Plans](https://developers.openai.com/cookbook/articles/codex_exec_plans)
- [Spec Kit Releases](https://github.com/github/spec-kit/releases)
- [Spec Kit Repository](https://github.com/github/spec-kit)
- [Cargo Workspaces](https://doc.rust-lang.org/cargo/reference/workspaces.html)
- [PyO3 User Guide](https://pyo3.rs/)
- [Maturin Project Layout](https://www.maturin.rs/project_layout.html)

## 17. Abschlussbewertung

Der vorgeschlagene Weg erhält den Wert des bestehenden Projekts und macht Rust zu einem überprüfbaren Lerninstrument. Die Migration beginnt nicht mit Infrastruktur oder UI, sondern mit einem grünen Oracle und einer sehr kleinen, deterministischen Fachfunktion. Dadurch ist jeder folgende Schritt fachlich messbar, reversibel und als Lernfortschritt nachvollziehbar.

Der nächste konkrete Schritt ist, den `/plan`-Prompt in Codex innerhalb des Mercator-Repositories auszuführen. Nach Prüfung des erzeugten Plans kann der zweite Prompt `001-rust-foundation` implementieren.
