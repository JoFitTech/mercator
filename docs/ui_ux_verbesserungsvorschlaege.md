# Mercator UI/UX – Verbesserungsvorschläge (Analystenfokus)

## Zielbild (Kurz)
Mercator soll sich wie ein fokussiertes Analysten-Werkzeug verhalten: schnell filtern, relevante Trades erkennen, Kandidaten priorisieren, Drilldown ohne Reibung.

## 1) Informationsarchitektur
- Navigation strikt entlang Aufgaben: **Overview → Explorer → Detailansicht**.
- Overview liefert Lagebild und Kandidatenvorschau, Explorer ist primäre Arbeitsfläche, Detailansicht ist Entscheidungs-/Audit-View.

## 2) Explorer (Kernarbeitsfläche)
- Primäre Filter immer sichtbar halten (Ticker, Insider, Richtung, Min Trade Value).
- Sekundäre Filter (Gate, Validation, Zeilenlimit, Aggregation) in progressive disclosure.
- Apply/Reset als Standard beibehalten, um unnötige Reruns zu vermeiden.
- Tabelle weiterhin nach Relevanz sortieren (Score + Trade Value).
- Optional als nächster Schritt: Row-Selection mit persistenter Selektion über Session State.

## 3) Tabellenqualität
- Spaltenpriorität: Symbol, Richtung, Score, Score Class, Trade Value, Gate, Validation zuerst.
- Konsistente Formate für Währung, Datum, Mengen.
- Zeilenhöhe/Tabellenhöhe stabil halten, damit visuelles Springen reduziert wird.

## 4) Drilldown-Logik
- Schnell-Drilldown im Explorer beibehalten (Ticker-Vorschau + Kernmetriken).
- Detailansicht als vollständige Analyse mit Profil, Trades und Raw/Audit.
- Optional als nächster Schritt: Direktübergabe des selektierten Tickers über Session State zwischen Explorer und Detailansicht.

## 5) Charts
- Nur Charts behalten, die eine konkrete Frage beantworten:
  - Zeitlicher Verlauf von Trade Value
  - Sektorverteilung
  - BUY/SELL-Balance
- Keine zusätzlichen dekorativen Charts ohne Erkenntnisgewinn.

## 6) Sidebar-Last
- Sidebar nur für App-/Betriebssteuerung.
- Technische Debug-Informationen nur im Advanced Mode.
- Fachliche Analyse-Interaktion primär in der Hauptfläche.

## 7) Performance-Wahrnehmung
- Form-gesteuerte Filter und reduzierte Reruns beibehalten.
- Optional: Caching für häufige Symbol-/Profilabrufe prüfen (abhängig von Datenkonsistenzanforderungen).

## 8) Accessibility & Lesbarkeit
- Kontrast und Fokuszustände regelmäßig manuell prüfen.
- Statusinformationen nie nur über Farbe kommunizieren (Label + Text beibehalten).
- Kompakte, konsistente Typo-Hierarchie beibehalten.

## 9) Nächste sinnvolle Iterationen
1. Persistente Row-Selection im Explorer.
2. Direkter „In Detailansicht öffnen“-Actionfluss.
3. Optionales Keyboard-First-Verhalten für häufige Analystenaufgaben.
4. Kleine visuelle Score-Badges (A-E) mit zusätzlicher Textkodierung (nicht nur Farbe).
