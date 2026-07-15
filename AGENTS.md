# Arbeitsanweisungen für Coding-Agenten

Diese Datei ist die verbindliche Arbeitsgrundlage für Änderungen im Mercator-Repository.
Sie gilt für Python, Rust, Tests und Projektdokumentation. Für den geplanten Rust-Lernpfad gelten die zusätzlichen Regeln in diesem Dokument besonders strikt.

## 1. Projektziel schützen

Mercator bleibt eine nachvollziehbare analytische Datenanwendung für Insider-Trades.
Der bestehende produktive Pfad ist weiterhin:

`FMP API -> lokale Validierung und Gates -> MongoDB Raw -> MySQL Clean -> Streamlit`

Rust wird schrittweise als optionaler Rechenkern ergänzt. Ein vollständiger Rewrite ist nicht erlaubt, solange kein dokumentierter Benchmark und keine fachliche Ergebnisparität vorliegen.

## 2. Verbindliche Architekturgrenze

In der ersten Rust-Ausbaustufe bleiben diese Bereiche in Python:

- Streamlit und UI-Zustand
- API-Orchestrierung und FMP-Rate-Limit-Behandlung
- MySQL- und MongoDB-Repositories
- Konfiguration und Betriebssteuerung
- bestehende Importabläufe

Rust darf zunächst nur deterministische, lokal testbare Fachlogik übernehmen:

- Transaktionscode-Klassifikation
- Validierung
- Gate-Entscheidungen
- 3-Tage-Akkumulation
- Scoring und technische Kennzahlen
- später optional Backtesting

Python muss bis zur bewussten Ablösung als Referenzimplementierung erhalten bleiben.

## 3. Lernmodus für Rust

Der Rust-Code soll nicht nur funktionieren. Er soll verständlich erklären, wie und warum er funktioniert.

### 3.1 Sprache

- Bezeichner im Code: Englisch
- Kommentare, Doc-Comments und Lernnotizen: Deutsch
- Fachbegriffe dürfen auf Englisch stehen, wenn sie im Code oder in der Domäne üblich sind

### 3.2 Jede Klasse beziehungsweise jeder Rust-Typ muss erklärt werden

Rust verwendet überwiegend `struct`, `enum` und `trait` statt klassischer Klassen. Für jeden neu angelegten öffentlichen Typ ist eine ausführliche `///`-Dokumentation Pflicht.

Die Erklärung muss mindestens enthalten:

1. fachlicher Zweck
2. technischer Zweck
3. Grund für einen eigenen Typ
4. Eingaben und Ausgaben
5. gültige Zustände und Invarianten
6. Fehlerfälle
7. Seiteneffekte
8. Bezug zur bisherigen Python-Komponente
9. ein kurzes Beispiel bei nicht trivialem Verhalten

Beispielstruktur:

```rust
/// Bewertet einen bereits validierten Insider-Trade gegen die statischen Mercator-Gates.
///
/// # Warum existiert dieser Service?
/// Die Gate-Logik wird von API-, Datenbank- und UI-Code getrennt, damit dieselben
/// Regeln in Python-Integration, Tests und späteren Backtests identisch verwendet werden.
///
/// # Eingabe
/// Ein `ValidatedInsiderTrade` und eine unveränderliche `GateConfig`.
///
/// # Ausgabe
/// Eine `GateDecision` mit Status und nachvollziehbaren Ablehnungsgründen.
///
/// # Invarianten
/// Der Service verändert den Eingabe-Trade nicht und führt keine API- oder DB-Aufrufe aus.
///
/// # Python-Referenz
/// Entspricht fachlich `src/preprocessing/gate_evaluator.py`.
pub struct GateEvaluator;
```

### 3.3 Kommentare im Implementierungscode

Es sollen viele hilfreiche Kommentare geschrieben werden. Kommentare dürfen jedoch nicht nur die Syntax wiederholen.

Pflichtkommentare:

- `//!` am Anfang jedes Rust-Moduls mit Zweck, Zuständigkeit und Abgrenzung
- `///` für jeden öffentlichen Typ, jedes öffentliche Feld und jede öffentliche Funktion
- Blockkommentare vor nicht offensichtlichen Fachregeln
- `// WARUM:` bei Entscheidungen, deren Grund nicht direkt aus dem Code hervorgeht
- `// INVARIANTE:` bei Zuständen, die während einer Berechnung erhalten bleiben müssen
- `// KOMPATIBILITÄT:` bei bewusster Nachbildung des Python-Verhaltens
- `// PERFORMANCE:` nur bei tatsächlich begründeten Optimierungen
- `// SICHERHEIT:` bei Validierungs-, Grenzwert- oder Fehlerbehandlungsentscheidungen

Nicht erlaubt:

```rust
// Erhöht i um 1.
i += 1;
```

Erwünscht:

```rust
// WARUM: Eine Lücke von mehr als drei Kalendertagen beendet die fachliche
// Akkumulationsgruppe. Dadurch werden zeitlich getrennte Entscheidungen desselben
// Insiders nicht fälschlich als ein einziges Signal behandelt.
if gap_days > config.window_days {
    start_new_group = true;
}
```

## 4. Dokumentation von Datenmodellen

Jedes öffentliche Feld eines Rust-Datenmodells erhält eine eigene `///`-Erklärung.
Die Erklärung muss Bedeutung, Einheit, erlaubte Werte und Herkunft nennen, soweit relevant.

Beispiel:

```rust
pub struct InsiderTrade {
    /// Börsensymbol zum Zeitpunkt der Meldung, normalisiert in Großbuchstaben.
    pub symbol: String,

    /// Gemeldeter Transaktionspreis in USD. Werte kleiner oder gleich null sind ungültig.
    pub price: Decimal,

    /// Anzahl der gemeldeten Wertpapiere. Der Wert muss positiv sein.
    pub securities_transacted: u64,
}
```

Unklare generische Felder wie `data`, `value`, `state` oder `result` sind zu vermeiden.

## 5. Fehlerbehandlung erklären

- Keine fachlichen Fehler über `panic!` behandeln
- Erwartbare Fehler als `Result<T, E>` modellieren
- Fachliche Statuswerte als `enum` modellieren
- Fehler-Enums vollständig dokumentieren
- Fehlertexte müssen konkret sein
- `unwrap()` und `expect()` sind im Anwendungscode nur erlaubt, wenn die Unmöglichkeit des Fehlers direkt begründet wird

Jeder Fehlerpfad muss erklären:

- was fehlgeschlagen ist
- warum der Fehler relevant ist
- ob der Datensatz verworfen, zurückgestellt oder weiterverarbeitet wird

## 6. Python-Rust-Integration

- Python ruft Rust immer batchweise auf
- Keine FFI-Aufrufe pro einzelner DataFrame-Zeile
- Die erste Integrationsstufe darf JSON oder Python-Dictionaries verwenden
- Vor einer Performancebewertung muss die Serialisierungszeit mitgemessen werden
- Die Python-Referenzfunktion bleibt verfügbar, bis Parität nachgewiesen ist
- Ein Feature-Flag oder klarer Adapter muss den Rückfall auf Python ermöglichen
- Rust darf keine direkten FMP-, MySQL-, MongoDB- oder Streamlit-Abhängigkeiten erhalten

## 7. Parität vor Geschwindigkeit

Jede nach Rust übertragene Funktion benötigt Vergleichstests gegen die Python-Referenz.

Pflichtfälle:

- normale Datensätze
- fehlende Pflichtfelder
- Preis null, negativ oder nicht parsebar
- Menge null oder nicht positiv
- unbekannter Transaktionscode
- Kauf und Verkauf strikt getrennt
- Randfälle exakt am 3-Tage-Fenster
- mehrere Preise und gewichteter Durchschnitt
- leere Eingaben
- Dubletten
- Datums- und Zeitzonenfälle

Eine Migration gilt nur als fachlich fertig, wenn Python und Rust für den definierten Testkorpus identische Ergebnisse erzeugen.

## 8. Benchmark-Regeln

Benchmarks dürfen erst nach bestandenen Paritätstests bewertet werden.

Zu messen sind getrennt:

- Parsing und Datentransfer
- Validierung
- Gate-Evaluation
- Akkumulation
- Scoring
- Gesamtlaufzeit einschließlich Python-Rust-Grenze
- Peak-Speicher, soweit mit vertretbarem Aufwand messbar

Datensatzgrößen:

- 1.000 Trades
- 100.000 Trades
- 1.000.000 Trades

Jeder Benchmark muss Hardware, Datengenerator, Anzahl der Wiederholungen und Warm-up dokumentieren.

## 9. Tests

Für Rust:

- Unit-Tests direkt am Modul
- Integrationstests unter `rust/mercator-core/tests/`
- Property-Tests für Gruppierungs- und Grenzwertlogik, wenn sinnvoll
- Benchmarks unter `rust/mercator-core/benches/`

Für Python:

- bestehende Tests dürfen nicht entfernt oder abgeschwächt werden
- neue Adapter benötigen eigene Tests
- Fallback auf Python muss getestet werden
- FFI-Fehler dürfen die Streamlit-App nicht unkontrolliert beenden

## 10. Lernprotokoll

Nach jedem abgeschlossenen Rust-Arbeitspaket ist `docs/RUST_LEARNING_LOG.md` zu ergänzen.
Jeder Eintrag enthält:

- Datum
- bearbeitete Komponente
- Lernziel
- umgesetzte Typen und Funktionen
- wichtige Rust-Konzepte
- Probleme
- Ursache
- Lösung
- verworfene Alternativen
- Testergebnis
- Benchmark, falls vorhanden
- offene Punkte

Keine erfundenen Ergebnisse eintragen. Nicht ausgeführte Tests und Benchmarks ausdrücklich als nicht ausgeführt markieren.

## 11. Änderungsumfang

- Pro Pull Request nur eine klar abgegrenzte Rust-Lernstufe
- Keine gleichzeitige Neustrukturierung des gesamten Python-Projekts
- Keine Änderungen an fachlichen Schwellenwerten im Rahmen einer technischen Migration
- Keine neue Abhängigkeit ohne Begründung im PR
- Keine Optimierung ohne vorherige Messung
- Keine Löschung der Python-Referenz vor einer separaten Entscheidung

## 12. Pull-Request-Nachweis

Jeder Rust-PR muss enthalten:

1. Ziel der Stufe
2. betroffene Python-Referenz
3. neue Rust-Typen mit kurzer Erklärung
4. fachliche Invarianten
5. Tests und tatsächliches Ergebnis
6. Benchmark und tatsächliches Ergebnis, falls ausgeführt
7. bekannte Abweichungen
8. Rückfallpfad
9. Aktualisierung des Lernprotokolls

## 13. Definition of Done für eine Rust-Komponente

Eine Komponente ist erst fertig, wenn:

- alle öffentlichen Typen und Funktionen dokumentiert sind
- nicht offensichtliche Fachregeln mit dem Grund kommentiert sind
- die Python-Referenz verlinkt oder genannt ist
- Unit-Tests vorhanden sind
- Paritätstests bestanden sind
- Fehlerfälle modelliert sind
- kein unnötiger I/O in den Rust-Core gelangt ist
- das Lernprotokoll aktualisiert ist
- tatsächlich ausgeführte Befehle und Ergebnisse im PR dokumentiert sind
