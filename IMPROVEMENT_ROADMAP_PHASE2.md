# Mercator UI/UX Verbesserungsplan – Phase 2

## Übersicht
Basierend auf der Audit-Analyse vom 28.04.2026 werden die folgenden Verbesserungen empfohlen. Diese Liste ist priorisiert nach Impact und Aufwand.

---

## 🔴 Hohe Priorität (P0 – Vor DB-II-Präsentation)

### P0.1: KPI-Karten mit aussagekräftigen Metriken füllen

**Problem:**
- Actionable Buys, Buy Candidates, Watchlist zeigen dauerhaft "0"
- Gibt dem Dashboard den Eindruck von fehlenden Daten

**Lösung:**
1. Prüfe `src/services/dashboard_service.py` – Methoden zur KPI-Berechnung:
   - `_calculate_kpi_actionable_buys()`
   - `_calculate_kpi_buy_candidates()`
   - `_calculate_kpi_watchlist()`
   
2. Verifiziere Datenpipeline von Raw → Clean Store

3. Alternative Metriken, falls Originale nicht verfügbar:
   - "Gültige Trades" (Trades mit PASS-Status)
   - "Durchschnittlicher Score" (Ø aus allen Trade-Scores)
   - "Aktive Insider" (Unique Insider im Zeitraum)
   - "Buy-Volumen (Million USD)" (aggregiertes Volumen)

**Betroffen:** `src/services/dashboard_service.py`, `src/ui/pages/dashboard_page.py`

**Aufwand:** 4-6 Stunden (Service-Debug + Metrik-Neu-Definition)

---

### P0.2: Data-Issues-Monitoring im Admin-Bereich

**Problem:**
- Data Issues wurden aus dem öffentlichen Dashboard entfernt ✅
- Es gibt aber keine Alternative im Admin-Bereich zur Diagnose

**Lösung:**
1. Neue Tab im Admin: "Datenqualität & Diagnostik"
2. Tabelle mit:
   - Fehltyp (TR-Fehler, Exchange-Fehler, Profil fehlt)
   - Anzahl betroffener Trades
   - Betroffene Insider/Unternehmen
   - Zeitraum des Fehlers

3. Optional: Export als CSV für Upstream-Benachrichtigung

**Betroffen:** `src/ui/pages/admin_page.py`, ggf. neuer Service `DiagnosticsService`

**Aufwand:** 6-8 Stunden

---

## 🟡 Mittlere Priorität (P1 – Post-Präsentation, aber vor nächster Iteration)

### P1.1: Größere/ergonomischere Zeilenauswahl in Tabellen

**Problem:**
- Benutzer müssen auf kleine Checkboxen klicken, um Zeilen auszuwählen
- Keine Möglichkeit, auf die Zeile selbst zu klicken

**Lösung Option A – Klick auf Zeile auslöst Auswahl:**
```python
# In src/ui/components/tables.py
# Neuer Parameter: clickable_rows = True
# Wenn Nutzer auf Zeile klickt, wird Checkbox gesetzt
```

**Lösung Option B – Größere Checkboxen:**
```css
/* In src/ui/ui_theme.py */
/* Vergrößere Checkbox-Größe via CSS */
input[type="checkbox"] {
    width: 24px;
    height: 24px;
    cursor: pointer;
}
```

**Betroffen:** `src/ui/components/tables.py`, `src/ui/ui_theme.py`

**Aufwand:** 2-3 Stunden

---

### P1.2: Sticky Tabellen-Header beim Scrollen

**Problem:**
- Bei großen Tabellen verschwindet der Header beim Scrollen
- Nutzer verliert den Kontext der Spalten

**Lösung:**
```html
<!-- Sticky Header CSS -->
<style>
    thead {
        position: sticky;
        top: 0;
        background: var(--mercator-ice-100);
        z-index: 10;
    }
</style>
```

**Betroffen:** `src/ui/components/tables.py`, `src/ui/ui_theme.py`

**Aufwand:** 1-2 Stunden

---

### P1.3: Erfolgsmeldungen auto-verstecken nach 3-5 Sekunden

**Problem:**
- `st.success()` und `st.info()` Meldungen bleiben dauerhaft sichtbar
- Machen die UI aufdringlich nach wiederholten Filteranwendungen

**Lösung:**
```python
# Custom Toast-Mechanismus
from src.ui.components.feedback import render_auto_dismiss_success

render_auto_dismiss_success(
    "Filter wurden angewendet", 
    duration_seconds=4
)
```

**Betroffen:** `src/ui/components/feedback.py` (neu), `src/ui/pages/trades_page.py`, `src/ui/pages/dashboard_page.py`

**Aufwand:** 2-3 Stunden

---

## 🟢 Niedrige Priorität (P2 – Optional, Polishing)

### P2.1: Pie-Charts in Balkendiagramme umwandeln

**Problem:**
- Pie-Charts sind bei vielen Segmenten schwer lesbar
- Barrierefrei nicht optimal

**Lösung:**
Ersetze `mark: { type: "arc" }` durch `mark: { type: "bar" }` und ändere Achsen-Encoding

```python
# src/ui/pages/dashboard_page.py
def _render_sector_bar_chart(df: pd.DataFrame, color_scale: dict | None = None) -> None:
    """Rendert Balkendiagramm (statt Pie) für Sektor-Verteilung."""
    # Ändere mark von "arc" zu "bar"
    # Ändere encoding: theta→x, color→y
```

**Hinweis:** Dies war laut Analyse ein expliziter Kundenwunsch. Bitte vor Umsetzung absprechen.

**Betroffen:** `src/ui/pages/dashboard_page.py` Zeile 137-165

**Aufwand:** 1-2 Stunden

---

### P2.2: Sprachliche Konsistenz (Backend cleanup)

**Problem:**
- Im Code tauchen Variationen auf wie `Praesentationsmodus` (ohne Umlaut)
- Nicht konsistent über alle Dateien hinweg

**Lösung:**
```bash
# Suche nach "Praesentationsmodus", "Praesentations", "Praesentation" etc.
grep -r "Praesen" src/
grep -r "tationsmod" src/

# Ersetze mit korrektem Unicode: "Präsentationsmodus"
```

**Betroffen:** Mehrere Backend-Dateien (Datenmodelle, Logger, etc.)

**Aufwand:** 1-2 Stunden (Code-Review und Replacement)

---

### P2.3: Caption-Texte unter Charts präzisieren

**Problem:**
- Captions sind teilweise vage ("Zeigt die Anzahl betroffener Unternehmen pro Größenklasse")
- Könnten hilfreicher sein

**Lösung:**
```python
# Bessere Captions mit Links zu Methodik-Seite

"Market-Cap-Verteilung",
"Zeigt, wie viele Unternehmen pro Marktkapitalisierungs-Klasse in den Trades vorkommen. "
"Größere Unternehmen sind überrepräsentiert."

# Link zur Methodik:
"[Wie wird Market-Cap klassifiziert?](/?page=Methodik)"
```

**Betroffen:** `src/ui/pages/dashboard_page.py` (diverse `st.caption()` Aufrufe)

**Aufwand:** 0.5-1 Stunde (reine Text-Updates)

---

## 🔵 Zukünftige Features (P3 – Nach DB-II)

### P3.1: Backend-Validierung fixen

**Problem (aus früheren Reviews):**
- `PRICE_INVALID` wird in `INVALID` konvertiert im Clean Store
- Preisfehler gehen damit verloren und können nicht separat analysiert werden

**Lösung:**
- Enum-Erweiterung oder separate Spalte für Original-Gate-Status
- Validierungs-Logik in `src/services/gate_evaluator_service.py` anpassen

**Betroffen:** `src/services/gate_evaluator_service.py`, Schema Migration erforderlich

**Aufwand:** 4-6 Stunden (Backend-Change + Tests + Migration)

---

### P3.2: Dashboard-Warnung für "Keine Daten"

**Problem:**
- Wenn für einen Zeitraum keine Daten existieren, wird ein Empty-State angezeigt
- Nutzer könnte aber das falsche Datum ausgewählt haben

**Lösung:**
```python
# Intelligentere Empty-State Nachricht:
earliest_trade = service.get_earliest_trade_date()
latest_trade = service.get_latest_trade_date()

if no_data_in_period:
    st.warning(
        f"Für den Zeitraum {date_from} bis {date_to} liegen keine Daten vor. "
        f"Verfügbare Daten: {earliest_trade} bis {latest_trade}. "
        f"[Zeitraum anpassen?](/?filters=...)"
    )
```

**Aufwand:** 2 Stunden

---

## 📋 Implementierungs-Roadmap

### Phase 2A (Vor DB-II Präsentation – diese Woche)
- [ ] P0.1: KPI-Karten debuggen und Metriken korrigieren
- [ ] P0.2: Data-Issues im Admin hinzufügen

### Phase 2B (Nach DB-II – nächste 2 Wochen)
- [ ] P1.1: Zeilenauswahl ergonomisch ausbauen
- [ ] P1.2: Sticky Headers implementieren
- [ ] P1.3: Toast-System verbessern
- [ ] P2.2: Backend-Sprachkonsistenz

### Phase 2C (Future – nach Feedbackrunde)
- [ ] P2.1: Pie→Bar-Umstellung (nur mit Kundenzustimmung)
- [ ] P3.1: Gate-Status-Validierung fixen
- [ ] P3.2: Intelligente Empty-States

---

## Testing-Strategie

### Unit Tests
```python
# test_dashboard_kpis.py
def test_kpi_actionable_buys_not_zero():
    """Validiert, dass Actionable Buys > 0 für Testdaten."""
    service = DashboardService()
    payload = service.build_dashboard_payload({"date_from": ..., "date_to": ...})
    assert payload["kpi_actionable_buys"] > 0
```

### Integration Tests
```python
# test_dashboard_page.py
def test_dashboard_renders_all_elements():
    """Rendert Dashboard mit Test-Daten vollständig."""
    # Streamlit test runner
```

### E2E Tests (Manuell)
- [ ] Alle 4 KPI-Karten zeigen Werte > 0
- [ ] Admin-Datenqualität-Tab ist erreichbar
- [ ] Zeilenauswahl funktioniert vollständig
- [ ] Sticky Headers bleiben sichtbar beim Scrollen

---

## Metriken für Erfolg

| Kriterium | Vorher | Ziel | KPI |
|---|---|---|---|
| KPI-Karten Datenqualität | 2/5 leer | 4/4 gefüllt | X/4 zeigen Werte > 0 |
| Dashboard Professional Rating | 3/5 | 5/5 | User Survey |
| Time-to-interact (Zeile auswählen) | 2 clicks | 1 click | User Testing |
| Backend Error Messages | Deutsch mit Umlauten mix | 100% konsistent | Code Review |

---

## Risk Assessment

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|---|---|---|---|
| KPI-Service wirft Fehler | Mittel | Hoch | Fallback Metriken vorab definieren |
| Sticky Header bricht Layout | Niedrig | Mittel | CSS in Branch testen, dann integrieren |
| Toast-System hat Timing-Bugs | Mittel | Niedrig | Timeout-Tests schreiben |

---

## Ressourcen & Support

- **Dashboard Service Code:** `src/services/dashboard_service.py` (439 Zeilen)
- **Admin Page Code:** `src/ui/pages/admin_page.py` (1540 Zeilen)
- **Dokumentation:** `docs/` Ordner
- **Kundenkontakt:** Für Pie→Bar Umstellung und weitere Priorisierung

---

**Status:** 📝 Geplant  
**Erstellt:** 28. April 2026  
**Fällig (Phase 2A):** 30. April 2026  
**Verwaltet durch:** GitHub Copilot + Development Team

