# Code-Änderungen: Dashboard & Navigation Cleanup

## Status: ✅ Abgeschlossen

**Datum:** 28. April 2026  
**Bearbeiter:** GitHub Copilot  
**Zweck:** Entfernung der Präsentationsmodus-Hinweise und Data-Issues-KPI vom öffentlichen Dashboard

---

## Geänderte Dateien

### 1. `src/ui/pages/dashboard_page.py`

#### Änderung 1.1: Data Issues KPI-Karte entfernt
**Zeile:** 353-359 (vorher: 353-363)  
**Beschreibung:** Die "Data Issues" KPI-Karte wurde aus der Karten-Liste entfernt, da diese nur im Admin-Bereich angezeigt werden soll.

```diff
kpis = [
    {"label": "Actionable Buys", "value": str(payload.get("kpi_actionable_buys", 0))},
    {"label": "Buy Candidates", "value": str(payload.get("kpi_buy_candidates", 0))},
    {"label": "Watchlist", "value": str(payload.get("kpi_watchlist", 0))},
    {"label": "Sell Warnings", "value": str(payload.get("kpi_sell_warnings", 0))},
-   {
-       "label": "Data Issues",
-       "value": str(int(payload.get("kpi_tr_not_found", 0)) + int(payload.get("kpi_exchange_resolution_issues", 0))),
-       "help": "Datenprobleme: TR/Exchange/Profile",
-   },
]
render_kpi_row(kpis)
```

**Auswirkung:** Dashboard zeigt nun 4 statt 5 KPI-Karten.

---

#### Änderung 1.2: Datenmodus-Anzeige aus der Fußzeile entfernt
**Zeile:** 361-364 (vorher: 366-370)  
**Beschreibung:** Der Modus-Label "Lokaler Präsentationsmodus" wurde aus der Fußzeile entfernt, da technische Details die professionelle Anmutung beeinträchtigen.

```diff
with st.container(border=True):
-   mode_label = "Lokaler Präsentationsmodus" if db_status and db_status.mongo.used_fallback else "Standardmodus"
    st.caption(
-       f"Zeitraum: {_format_period_label(filters)} | {_format_data_freshness_label(payload.get('last_update'))} | Datenmodus: {mode_label}"
+       f"Zeitraum: {_format_period_label(filters)} | {_format_data_freshness_label(payload.get('last_update'))}"
    )
```

**Auswirkung:** Fußzeile ist kürzer und fokussierter, zeigt nur relevante Informationen für den Nutzer.

---

### 2. `src/app/navigation.py`

#### Änderung 2.1: "Uni-Datenbank nicht erreichbar"-Nachricht entfernt
**Zeile:** 304-310 (vorher: 304-312)  
**Beschreibung:** Die spezifische Fallback-Error-Nachricht "Uni-Datenbank nicht erreichbar. Lokaler Präsentationsmodus aktiv." wurde entfernt.

```diff
if db_status.mongo.used_fallback:
    st.caption("Mongo Fallback: aktiv")
-if db_status.mongo.requested_target == "uni" and db_status.mongo.active_target == "local" and db_status.mongo.used_fallback:
-    st.caption("Uni-Datenbank nicht erreichbar. Lokaler Präsentationsmodus aktiv.")
-elif db_status.mongo.messages:
+if db_status.mongo.messages:
    prefix = "Hinweis" if db_status.mongo.is_connected else "Grund"
    short_message = str(db_status.mongo.messages[0]).split("\n", 1)[0][:140]
    st.caption(f"{prefix}: {short_message}")
    with st.expander("Details", expanded=False):
        for msg in db_status.mongo.messages:
            st.code(str(msg), language="text")
```

**Auswirkung:** 
- Sidebar System-Status zeigt nicht mehr die technische Fallback-Nachricht
- Mongo Fallback ist weiterhin sichtbar als "Mongo Fallback: aktiv" (technical indicator)
- Andere Fehlermeldungen werden weiterhin normal angezeigt

---

## Auswirkungen auf Funktionalität

### Betroffene Komponenten:
- Dashboard KPI-Anzeige
- Dashboard Fußzeile
- Sidebar System-Status

### Nicht betroffene Komponenten:
- Charts und Visualisierungen (unverändert)
- Filter und Navigation (unverändert)
- Datenquellen und Services (unverändert→ rein UI-Change)
- Admin-Bereich (unverändert)

### Neue Einschränkungen:
- ⚠️ Data Issues werden nicht mehr auf dem öffentlichen Dashboard gezählt/angezeigt
  - Lösung: Im Admin-Bereich als separate Ansicht implementierbar

### Gewonnene Verbesserungen:
- ✅ Professionellere UI ohne technische Details im Frontend
- ✅ Weniger ablenkende Meldungen für End-User
- ✅ Klarere Struktur: 4 operative KPI-Karten statt Mix aus operativ und diagnostisch

---

## Validierungsschritte

### Unit-Tests:
- [ ] `test_dashboard_kpi_count()` – Validiert, dass genau 4 KPIs zurückgegeben werden
- [ ] `test_dashboard_footer_no_mode_label()` – Prüft, dass "Datenmodus" nicht mehr in Footer ist
- [ ] `test_navigation_status_no_uni_message()` – Verifiziert, dass Uni-Nachricht nicht mehr gesendet wird

### Integration-Tests:
- [ ] Vollständiger Dashboard-Durchlauf mit verschiedenen Zeiträumen
- [ ] Sidebar Navigation und System-Status Rendering
- [ ] Filter-Anwendung und Reset

### UI/E2E-Tests (Manuell):
- [ ] 4 KPI-Karten visuell prüfen (nicht 5)
- [ ] Fußzeile liest "Zeitraum: 29.03.2026 bis 28.04.2026 | Datenstand bis 27.04.2026"
- [ ] Sidebar zeigt "Mongo Fallback: aktiv" (falls Fallback verwendet wird), aber NICHT "Uni-Datenbank nicht erreichbar"
- [ ] Alle anderen Dashboard-Features funktionieren unverändert

---

## Rollback-Plan

Falls problematisch:
```bash
git revert <commit-hash>
```

Oder manual restore von backup:
```python
# In src/ui/pages/dashboard_page.py Zeile 358 – Data Issues KPI hinzufügen:
{
    "label": "Data Issues",
    "value": str(int(payload.get("kpi_tr_not_found", 0)) + int(payload.get("kpi_exchange_resolution_issues", 0))),
    "help": "Datenprobleme: TR/Exchange/Profile",
},

# In src/app/navigation.py Zeile 304 – Uni-Nachricht hinzufügen:
if db_status.mongo.requested_target == "uni" and db_status.mongo.active_target == "local" and db_status.mongo.used_fallback:
    st.caption("Uni-Datenbank nicht erreichbar. Lokaler Präsentationsmodus aktiv.")
```

---

## Abhängigkeiten und Abhängige

### Interne Abhängigkeiten:
- Keine neuen Dependencies
- Keine geänderten Service-Aufrufe
- Keine veränderten Datenstrukturen

### Abhängige Komponenten:
- Dashboard-Tests (müssen eventuell KPI-Anzahl anpassen: 5 → 4)
- ZukunftsAnforderung: Admin-Page sollte Data Issues Tabelle anzeigen

---

## Performance-Implikationen

- ✅ **Positive Implikation:** Weniger UI-Rendering (eine KPI weniger)
- ✅ **Neutral:** Keine neuen Service-Calls
- ✅ **Neutral:** Dashboard-Load-Time unverändert

---

## Dokumentation

### User-Facing Änderungen:
- Dashboard zeigt 4 statt 5 KPI-Karten
- Fußzeile enthält keine Modusinformation mehr
- Admin-Nutzer sehen möglicherweise weniger diagnostische Information im öffentlichen Dashboard

### Developer-Facing Änderungen:
- Zwei Dateien angepasst
- Entfernung Hard-Coded Kurztext
- Service-Layer unverändert (kein Refactoring erforderlich)

---

## Genehmigungen

| Rolle | Status | Datum |
|---|---|---|
| Code Review | ⏳ Pending | — |
| QA Sign-Off | ⏳ Pending | — |
| Product Owner | ⏳ Pending | — |

---

**Commit Message (vorgeschlagen):**
```
fix(dashboard): remove data-issues-kpi and presentation-mode indicators

- Remove Data Issues KPI card from dashboard (move to admin)
- Remove "Lokaler Präsentationsmodus" from footer
- Remove "Uni-Datenbank nicht erreichbar" error message from sidebar
- Keep operational KPIs (4 instead of 5)
- Improve professional appearance and reduce technical noise

Fixes: Audit findings from 28.04.2026
```

---

**Datei erstellt:** 28. April 2026  
**Version:** 1.0  
**Status:** Bereit für Review und Deployment

