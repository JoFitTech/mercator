# Rust-Lern- und Migrationsplan für Mercator

## 1. Ziel

Mercator wird nicht vollständig nach Rust umgeschrieben.
Stattdessen entsteht ein kleiner, deterministischer Rechenkern, an dem Rust systematisch gelernt und dessen Nutzen objektiv gemessen wird.

Der Plan verfolgt drei Ziele:

1. Rust anhand echter Mercator-Fachlogik lernen
2. fachlich identische Ergebnisse zur Python-Implementierung sicherstellen
3. Performance nur dort verbessern, wo Messungen einen Engpass zeigen

## 2. Ausgangslage

Der bestehende Mercator-Pfad bleibt zunächst unverändert:

`FMP API -> Validation/Gates -> MongoDB Raw + MySQL Clean -> Streamlit UI`

Die Gesamtlaufzeit wird aktuell stark durch externe API-Aufrufe, Datenbankzugriffe und UI-Verarbeitung beeinflusst.
Rust kann diese Wartezeiten nicht beseitigen.

Rust ist deshalb zuerst für lokale CPU-Logik vorgesehen:

- Transaktionscode-Klassifikation
- Validierung
- Gate-Evaluation
- 3-Tage-Akkumulation
- Scoring
- technische Kennzahlen
- später optional Backtesting

## 3. Zielarchitektur

```text
Streamlit UI
    |
Python Application Layer
    |-- FMP API
    |-- MySQL
    |-- MongoDB
    |-- Orchestrierung
    |
Python Adapter
    |-- Python-Referenz
    |-- optionaler Rust-Aufruf
    |-- Fallback bei Fehlern
    |
mercator-core in Rust
    |-- Domain-Typen
    |-- Validation
    |-- Gates
    |-- Akkumulation
    |-- Scoring
    |-- Benchmarks
```

Der Rust-Core führt keinen Netzwerk- oder Datenbankzugriff aus.
Er erhält Daten, verarbeitet sie deterministisch und gibt Ergebnisse zurück.

## 4. Verzeichnisstruktur

```text
mercator/
├── src/                              bestehende Python-Anwendung
├── rust/
│   └── mercator-core/
│       ├── Cargo.toml
│       ├── pyproject.toml            Maturin-Konfiguration
│       ├── src/
│       │   ├── lib.rs
│       │   ├── domain/
│       │   │   ├── mod.rs
│       │   │   ├── insider_trade.rs
│       │   │   ├── transaction_code.rs
│       │   │   ├── validation.rs
│       │   │   ├── gate.rs
│       │   │   ├── accumulation.rs
│       │   │   └── score.rs
│       │   ├── services/
│       │   │   ├── mod.rs
│       │   │   ├── transaction_code_classifier.rs
│       │   │   ├── validation_service.rs
│       │   │   ├── gate_evaluator.rs
│       │   │   ├── accumulation_service.rs
│       │   │   └── scoring_service.rs
│       │   └── python/
│       │       ├── mod.rs
│       │       └── api.rs
│       ├── tests/
│       └── benches/
├── docs/
│   ├── RUST_MIGRATION_PLAN.md
│   └── RUST_LEARNING_LOG.md
└── tests/
    └── rust_parity/
```

## 5. Geplante Typen und ihre Aufgaben

Rust besitzt nicht dieselbe Klassenstruktur wie Python.
Die fachlichen Objekte werden überwiegend als `struct` und `enum` modelliert.
Services können zustandslose `struct`-Typen oder reine Funktionen sein.

### 5.1 `RawInsiderTradeDto`

Zweck:

- bildet die für den Rust-Core benötigten Felder eines eingehenden Trades ab
- erlaubt fehlende und noch nicht validierte Werte
- trennt unsichere Eingangsdaten von fachlich gültigen Daten

Warum eigener Typ:

Ein roher API-Datensatz darf nicht versehentlich wie ein validierter Trade behandelt werden.
Der Typ macht diesen Unterschied im Compiler sichtbar.

Vorgesehene Felder:

- `symbol: Option<String>`
- `filing_date: Option<String>`
- `transaction_date: Option<String>`
- `price: Option<Decimal>`
- `securities_transacted: Option<i64>`
- `acquisition_or_disposition: Option<String>`
- `form_type: Option<String>`
- `security_name: Option<String>`
- `transaction_type: Option<String>`
- `reporting_name: Option<String>`

Python-Referenz:

- Normalisierung im Import- und Preprocessing-Pfad

### 5.2 `ValidatedInsiderTrade`

Zweck:

- repräsentiert einen Trade, dessen Pflichtfelder geprüft und typisiert sind
- wird erst nach erfolgreicher Validierung erzeugt

Warum eigener Typ:

Nach der Konvertierung müssen nachfolgende Services nicht erneut prüfen, ob Symbol, Preis, Menge und Datum grundsätzlich vorhanden sind.

Wichtige Invarianten:

- Symbol ist nicht leer
- Preis ist größer als null
- Menge ist größer als null
- Datumswerte sind erfolgreich geparst

### 5.3 `TradeDirection`

Mögliche Werte:

- `Buy`
- `Sell`
- `Unknown`

Zweck:

- ersetzt uneinheitliche Stringwerte wie `A`, `D`, `BUY` und `SELL`
- verhindert unkontrollierte Stringvergleiche in mehreren Services

### 5.4 `TransactionCode`

Zweck:

- bildet bekannte SEC-Transaktionscodes typisiert ab
- enthält einen expliziten `Unknown(String)`-Fall

Warum kein einfacher String:

Die Menge zulässiger und fachlich relevanter Werte ist begrenzt.
Ein `enum` macht vollständige `match`-Prüfungen möglich.

### 5.5 `TransactionClass`

Mögliche Werte:

- `CoreBuy`
- `CoreSell`
- `SecondarySignal`
- `ManualReview`
- `ExcludedFromCore`

Zweck:

- trennt regulatorischen Code und Mercator-Bewertung
- macht die lokale Taxonomie explizit und testbar

Python-Referenz:

- `src/services/transaction_code_classifier.py`

### 5.6 `ValidationStatus`

Mögliche Werte:

- `Valid`
- `PriceInvalid`
- `QuantityInvalid`
- `MissingSymbol`
- `MissingFilingDate`
- `MissingTransactionDate`
- `ParseError`

Zweck:

- ersetzt uneinheitliche Fehlerstrings
- erlaubt gezielte Weiterverarbeitung und Protokollierung

### 5.7 `ValidationError`

Zweck:

- transportiert konkrete technische und fachliche Validierungsfehler
- enthält bei Bedarf Feldname und problematischen Wert

Abgrenzung:

`ValidationStatus` beschreibt den fachlichen Zustand eines Datensatzes.
`ValidationError` beschreibt, warum eine Konvertierung oder Prüfung fehlgeschlagen ist.

### 5.8 `GateConfig`

Zweck:

- enthält unveränderliche Gate-Parameter
- verhindert versteckte globale Konfiguration im Rust-Core

Vorgesehene Felder:

- `minimum_trade_value`
- `required_form_type`
- `require_purchase_event`
- `require_common_stock`
- `maximum_filing_age_days`

### 5.9 `GateStatus`

Mögliche Werte:

- `Pass`
- `Pending`
- `PreGateFail`
- `Reject`
- `ManualReview`

Zweck:

- bildet den fachlichen Zustand nach Gate-Prüfung ab
- bleibt von UI-Farben und Datenbankdarstellung unabhängig

### 5.10 `GateReason`

Mögliche Gründe:

- falscher Formtyp
- Transaktionswert unter Mindestgrenze
- ungeeigneter Transaktionscode
- zu altes Filing
- ungeeigneter Instrumenttyp
- kein echter Kauf

Zweck:

- eine Entscheidung darf nicht nur einen Status liefern
- die UI und spätere Evaluation benötigen nachvollziehbare Gründe

### 5.11 `GateDecision`

Zweck:

- bündelt `GateStatus` und alle `GateReason`-Werte
- kann zusätzlich berechnete Werte wie `trade_value` enthalten

Invariante:

Ein `Pass` darf keine ablehnenden Gründe enthalten.

### 5.12 `AccumulationKey`

Bestandteile:

- Symbol
- Reporting Name oder CIK
- Richtung

Zweck:

- definiert explizit, welche Trades fachlich zusammengehören können
- verhindert versehentliche Mischung von Käufen und Verkäufen

### 5.13 `AccumulationGroup`

Zweck:

- enthält eine Gruppe zeitnaher Trades
- berechnet Menge, Gesamtwert, gewichteten Preis, Start- und Enddatum

Wichtige Invarianten:

- alle Trades haben denselben `AccumulationKey`
- Zeitlücke zwischen aufeinanderfolgenden Trades überschreitet das konfigurierte Fenster nicht
- gewichteter Preis verwendet Gesamtwert geteilt durch Gesamtmenge

Python-Referenz:

- `src/services/accumulation_service.py`

### 5.14 `ScoreComponent`

Zweck:

- repräsentiert einen einzelnen nachvollziehbaren Score-Anteil

Vorgesehene Felder:

- Name
- Rohwert
- Punkte
- maximal mögliche Punkte
- Begründung

Warum eigener Typ:

Der finale Score soll in UI, Tests und Methodikseite auf dieselbe Weise erklärbar bleiben.

### 5.15 `ScoreBreakdown`

Zweck:

- enthält alle Score-Komponenten
- berechnet Gesamtwert und Score-Klasse

Invariante:

Der Gesamtwert muss der Summe der Komponenten entsprechen.

### 5.16 `TransactionCodeClassifier`

Zweck:

- ordnet `TransactionCode` einer `TransactionClass` zu

Eigenschaften:

- zustandslos
- deterministisch
- keine API- oder Datenbankzugriffe

Erste Rust-Lernstufe:

Dieser Service ist klein, fachlich klar und eignet sich für `enum`, `match`, Module und Unit-Tests.

### 5.17 `ValidationService`

Zweck:

- konvertiert `RawInsiderTradeDto` in `ValidatedInsiderTrade`
- sammelt oder meldet konkrete Validierungsfehler

Rust-Lerninhalte:

- `Option`
- `Result`
- eigene Fehler-Enums
- Parsing
- Ownership und Referenzen

### 5.18 `GateEvaluator`

Zweck:

- bewertet einen validierten Trade gegen `GateConfig`
- liefert eine vollständig nachvollziehbare `GateDecision`

Abgrenzung:

Der Service bewertet nur lokale Fachregeln.
Er entscheidet nicht, ob anschließend eine FMP-API aufgerufen wird.
Diese Orchestrierung bleibt in Python.

### 5.19 `AccumulationService`

Zweck:

- sortiert und gruppiert validierte Trades nach Schlüssel und Zeitfenster
- erzeugt `AccumulationGroup`-Werte

Rust-Lerninhalte:

- Collections
- Sortierung
- Iteratoren
- Datumsarithmetik
- Borrowing
- effiziente Batch-Verarbeitung

### 5.20 `ScoringService`

Zweck:

- berechnet aus bereits verfügbaren Merkmalen einen finalen, erklärbaren Score

Abgrenzung:

Der Service lädt keine historischen Kurse.
Python übergibt die bereits berechneten oder geladenen Merkmale.

### 5.21 `PythonApi`

Zweck:

- bildet die schmale PyO3-Grenze zwischen Python und Rust
- konvertiert Batch-Eingaben und Batch-Ausgaben

Wichtige Regel:

Es gibt keine FFI-Aufrufe pro Trade.
Ein kompletter Batch wird in einem Aufruf verarbeitet.

## 6. Umsetzungsphasen

### Phase 0: Baseline und Messbarkeit

Aufgaben:

- bestehende Python-Funktionen und Testfälle identifizieren
- repräsentativen Testkorpus erstellen
- Laufzeit der aktuellen Python-Pfade messen
- fachliche Schwellenwerte einfrieren

Ergebnis:

- dokumentierte Baseline
- keine Rust-Integration

Abnahmekriterien:

- Testkorpus enthält normale und fehlerhafte Trades
- aktuelle Python-Ergebnisse sind gespeichert
- Messmethode ist reproduzierbar

### Phase 1: Rust-Projektgerüst und Code-Klassifikation

Aufgaben:

- Cargo-Projekt erstellen
- `TransactionCode` und `TransactionClass` implementieren
- `TransactionCodeClassifier` implementieren
- ausführliche deutsche Doc-Comments schreiben
- Unit-Tests gegen die bestehende Taxonomie erstellen

Abnahmekriterien:

- alle Codes sind abgedeckt
- unbekannte Codes sind explizit behandelt
- keine Python-Integration notwendig

### Phase 2: Validierung

Aufgaben:

- rohe und validierte Trade-Typen implementieren
- Datums- und Zahlenprüfung implementieren
- Fehler-Enums dokumentieren
- Paritätstests gegen Python erstellen

Abnahmekriterien:

- identische Entscheidung für alle Baseline-Fälle
- kein `panic!` bei fehlerhaften Eingaben

### Phase 3: Gate-Evaluation

Aufgaben:

- `GateConfig`, `GateStatus`, `GateReason` und `GateDecision` implementieren
- Gate-Regeln übertragen
- Gründe vollständig ausgeben
- Python-Rust-Parität testen

Abnahmekriterien:

- keine Änderung an Schwellenwerten
- Status und Gründe stimmen mit der Referenz überein

### Phase 4: 3-Tage-Akkumulation

Aufgaben:

- Schlüssel und Gruppen implementieren
- Sortierung und Fensterlogik übertragen
- gewichteten Durchschnitt implementieren
- Kauf und Verkauf strikt trennen
- Randfälle für genau drei und mehr als drei Tage testen

Abnahmekriterien:

- Gruppenanzahl und Gruppeninhalt sind identisch
- Mengen, Werte und gewichtete Preise sind identisch innerhalb definierter Rundung

### Phase 5: Scoring

Aufgaben:

- Score-Komponenten modellieren
- bestehende Gewichtung unverändert übertragen
- Score-Breakdown ausgeben
- Score-Klassen testen

Abnahmekriterien:

- Gesamtwerte und Klassen stimmen überein
- jede Komponente ist einzeln nachvollziehbar

### Phase 6: PyO3-Integration

Aufgaben:

- Maturin und PyO3 konfigurieren
- Batch-API implementieren
- Python-Adapter mit Feature-Flag erstellen
- Python-Fallback implementieren
- FFI-Fehler kontrolliert behandeln

Abnahmekriterien:

- bestehende App startet ohne Rust-Erweiterung
- Rust kann optional aktiviert werden
- Fehler im Rust-Modul führen zum definierten Python-Fallback

### Phase 7: Benchmarks und Entscheidung

Aufgaben:

- 1.000, 100.000 und 1.000.000 Trades testen
- reine Rechenzeit und Gesamtlaufzeit messen
- Datentransfer separat messen
- Speicherverbrauch soweit möglich erfassen

Entscheidungsregeln:

- fachliche Parität ist zwingend
- ein Geschwindigkeitsvorteil muss einschließlich FFI-Grenze bestehen
- bei geringem Vorteil bleibt Python Standard
- Lernwert allein rechtfertigt den experimentellen Rust-Core, aber nicht die Entfernung der Python-Referenz

### Phase 8: Optionales Backtesting

Erst nach erfolgreicher Kernintegration.

Mögliche Funktionen:

- Einstieg am ersten Handelstag nach Filing
- feste Haltedauern
- Gebühren und Slippage
- Benchmarkvergleich
- Parameterläufe über viele Symbole und Zeiträume

Dieser Bereich besitzt voraussichtlich den größten realen Performancehebel.

## 7. Teststrategie

### 7.1 Golden-Master-Parität

Für einen festen Eingabekorpus werden Python-Ausgaben gespeichert und mit Rust-Ausgaben verglichen.

Verglichen werden:

- Status
- Gründe
- normalisierte Werte
- Gruppen-IDs oder fachlich äquivalente Gruppenzuordnung
- aggregierte Mengen
- Gesamtwerte
- gewichtete Preise
- Score-Komponenten
- Gesamt-Score
- Score-Klasse

### 7.2 Unit-Tests

Jeder Typ und Service erhält lokale Tests.
Tests sollen die fachliche Absicht benennen und nicht nur Implementierungsdetails prüfen.

### 7.3 Property-Tests

Geeignete Eigenschaften:

- Gesamtmenge einer Gruppe entspricht der Summe der Einzelmengen
- Käufe und Verkäufe befinden sich nie in derselben Gruppe
- Sortierreihenfolge der Eingabe verändert das fachliche Ergebnis nicht
- ein `Pass` enthält keine Ablehnungsgründe
- Score-Gesamtwert entspricht der Summe der Komponenten

## 8. Benchmarkstrategie

Zu jeder Größe werden mehrere Durchläufe nach Warm-up ausgeführt.

Messpunkte:

1. Python-Referenz ohne I/O
2. Rust-Core ohne Python-Grenze
3. Rust-Aufruf aus Python einschließlich Konvertierung
4. vollständiger lokaler Verarbeitungspfad ohne externe API

Ein Ergebnis wie „Rust ist zehnmal schneller“ ist nur zulässig, wenn klar angegeben wird, welcher Messpunkt gemeint ist.

## 9. Risiken und Gegenmaßnahmen

### Risiko: unnötiger Rewrite

Gegenmaßnahme:

- kleine Phasen
- Python bleibt Referenz
- pro PR nur eine Komponente

### Risiko: andere fachliche Ergebnisse

Gegenmaßnahme:

- Golden-Master-Tests
- unveränderte Schwellenwerte
- dokumentierte Rundungsregeln

### Risiko: FFI-Aufwand vernichtet Performance

Gegenmaßnahme:

- Batch-Aufrufe
- Datentransfer separat messen
- keine Aufrufe pro DataFrame-Zeile

### Risiko: Kommentare veralten

Gegenmaßnahme:

- Kommentare beschreiben Invarianten und Gründe
- PR-Review prüft Dokumentation
- Lernprotokoll und Tests werden gemeinsam aktualisiert

### Risiko: zu hohe Lernkomplexität

Gegenmaßnahme:

- Beginn mit Code-Klassifikation
- erst danach Fehlerbehandlung, Gruppierung und FFI
- keine Datenbank- oder Async-Komplexität in den ersten Phasen

## 10. Erste konkrete Aufgabe

Der erste Implementierungs-PR soll ausschließlich enthalten:

- Cargo-Grundgerüst
- `TransactionCode`
- `TransactionClass`
- `TransactionCodeClassifier`
- deutsche Modul- und Typdokumentation
- Unit-Tests für alle bekannten Codes
- Eintrag im Lernprotokoll

Nicht enthalten:

- PyO3
- Datenbankzugriffe
- FMP-Aufrufe
- Streamlit-Anpassungen
- Gate-Logik
- Performanceversprechen

## 11. Erfolgskriterien des Gesamtvorhabens

Das Vorhaben ist erfolgreich, wenn:

- Rust anhand realer Mercator-Logik nachvollziehbar gelernt wurde
- jeder neue Typ fachlich und technisch dokumentiert ist
- Python und Rust identische Ergebnisse liefern
- Benchmarks reproduzierbar sind
- die Anwendung jederzeit auf die Python-Referenz zurückfallen kann
- nur messbar sinnvolle Komponenten dauerhaft im Rust-Core bleiben
