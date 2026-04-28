# 🧪 Mercator Audit Fixes – Testing Checklist

**Datum:** 28. April 2026  
**Fixes angewendet:** Dashboard + Navigation Cleanup  
**Tester:** [Ihr Name]  
**Datum getestet:** ___________  
**Status:** [ ] ✅ Bestanden | [ ] ⚠️ Mit Anmerkungen | [ ] ❌ Fehler gefunden

---

## 📋 Pre-Test Vorbereitung

### Setup
- [ ] Branch/Commit mit Fixes wird deployed
- [ ] Browser-Cache geleert (Ctrl+Shift+Del)
- [ ] Fresh Streamlit Session (F5 oder restart)
- [ ] Test-DB mit Daten gefüllt (29.03.2026 – 28.04.2026)

### Umgebung
- [ ] URL: https://could-alabama-hanging-guided.trycloudflare.com/
- [ ] Oder lokal: http://localhost:8501
- [ ] Datenbank beiden erreichbar (MySQL + MongoDB)

---

## 🎯 Test 1: Dashboard KPI-Karten

### ✅ Erwartung
- Exakt **4 KPI-Karten** sichtbar (nicht 5)
- Karten sind: Actionable Buys, Buy Candidates, Watchlist, Sell Warnings
- **KEINE** "Data Issues" Karte mehr

### 🔍 Test-Schritte
1. Öffne Dashboard
2. Scrolle nach oben zur KPI-Sektion
3. **Zähle die Karten:** _____ (soll 4 sein)

### 📌 Karten-Kontrolle
- [ ] Karte 1: "Actionable Buys" – Wert sichtbar (z.B. "0" oder "42")
- [ ] Karte 2: "Buy Candidates" – Wert sichtbar
- [ ] Karte 3: "Watchlist" – Wert sichtbar
- [ ] Karte 4: "Sell Warnings" – Wert sichtbar (würde "23" sein laut Audit)
- [ ] KEIN "Data Issues" Label sichtbar

### 📸 Screenshot-Referenz
1. KPI-Sektion vor Fix: 5 Karten + "Data Issues"  
2. KPI-Sektion nach Fix: 4 Karten, kein "Data Issues"

### ❌ Falls fehlgeschlagen
```
Symptom: Immer noch 5 Karten
Ursache: Datei nicht aktualisiert oder Cache-Problem
Lösung:
1. Prüfe ob Datei src/ui/pages/dashboard_page.py Zeile 353-359 korrekt
2. Streamlit cache clearen: rm -r ~/.streamlit/cache_*
3. Seite neu laden
```

---

## 🎯 Test 2: Dashboard Fußzeile (Datenmodus entfernt)

### ✅ Erwartung
- Fußzeile zeigt: `Zeitraum: 29.03.2026 bis 28.04.2026 | Datenstand bis 27.04.2026`
- **KEIN** "Datenmodus: Lokaler Präsentationsmodus" Text

### 🔍 Test-Schritte
1. Dashboard laden
2. Nach Filter-Box nach unten scrollen
3. Container mit grauem Hintergrund suchen (oberhalb der Charts)
4. Lese den Caption-Text

### 📋 Text-Prüfung
- [ ] Text beginnt mit "Zeitraum:"
- [ ] Text enthält Datum von bis Datum (z.B. "29.03.2026 bis 28.04.2026")
- [ ] Text enthält "Datenstand bis" 
- [ ] **KEINE** Erwähnung von "Datenmodus"
- [ ] **KEINE** Erwähnung von "Präsentationsmodus"
- [ ] **KEINE** Erwähnung von "Standardmodus" oder "Lokaler"

### Akzeptierte Variationen
| ✅ OK | ❌ NICHT OK |
|---|---|
| "Zeitraum: 29.03.2026 bis 28.04.2026 \\| Datenstand bis 27.04.2026" | "... \\| Datenmodus: Lokaler Präsentationsmodus" |
| "Zeitraum: (leer) \\| Datenstand bis 27.04.2026" | "... \\| Datenmodus: Standardmodus" |

### ❌ Falls fehlgeschlagen
```
Symptom: "Datenmodus: Lokaler Präsentationsmodus" ist noch sichtbar
Ursache: dashboard_page.py Zeile 361-364 nicht angepasst
Lösung: 
1. Öffne src/ui/pages/dashboard_page.py
2. Suche nach "mode_label"
3. Diese 2 Zeilen sollten gelöscht sein:
   - mode_label = "Lokaler Präsentationsmodus" if ...
   - | Datenmodus: {mode_label}
4. Stattdessen nur noch f"... {_format_data_freshness_label(...)}"
```

---

## 🎯 Test 3: Sidebar System-Status (Uni-Datenbank Nachricht weg)

### ✅ Erwartung
- Sidebar expandiert "System-Status"
- Zeigt MongoDB Status (Online/Offline)
- **KEINE** Nachricht "Uni-Datenbank nicht erreichbar. Lokaler Präsentationsmodus aktiv."

### 🔍 Test-Schritte
1. Öffne Dashboard oder beliebige Seite
2. Linke Sidebar → Section "Mercator"
3. Klick auf "System-Status" (sollte aufgeklappt sein)
4. Lese alle Caption-Texte

### 📋 Text-Prüfung
- [ ] ":green[MongoDB: Online]" oder ":red[MongoDB: Offline]" sichtbar
- [ ] Optional "Mongo Target: local" oder "Mongo Target: uni"
- [ ] Optional "Mongo Fallback: aktiv" (DARF sichtbar sein!)
- [ ] **KEIN** "Uni-Datenbank nicht erreichbar" Text
- [ ] **KEIN** "Lokaler Präsentationsmodus aktiv" Text

### 🟢 Normal (wenn Fallback NICHT aktiv)
```
MongoDB: Online
Mongo Target: uni
Betriebsmodus: Schreiben aktiv
```

### 🟡 Akzeptabel (wenn Fallback aktiv – lokale DB)
```
MongoDB: Online
Mongo Target: local
Mongo Fallback: aktiv           ← OK, darf sichtbar sein
Betriebsmodus: Lesemodus
```

### ❌ NICHT AKZEPTABEL
```
MongoDB: Online
Mongo Target: local
Mongo Fallback: aktiv
[FEHLER] Uni-Datenbank nicht erreichbar. Lokaler Präsentationsmodus aktiv.  ← FALSCH!
```

### ❌ Falls fehlgeschlagen
```
Symptom: "Uni-Datenbank nicht erreichbar. Lokaler Präsentationsmodus aktiv." ist sichtbar
Ursache: navigation.py Zeile 304-305 nicht angepasst
Lösung:
1. Öffne src/app/navigation.py
2. Suche nach def render_system_status_sidebar
3. Zeilen 304-305 sollten GELÖSCHT sein:
   if db_status.mongo.requested_target == "uni" and ...
       st.caption("Uni-Datenbank nicht erreichbar...")
   elif db_status.mongo.messages:
4. Stattdessen direkt:
   if db_status.mongo.messages:
```

---

## 🎯 Test 4: Dashboard Funktionalität (Regression)

### ✅ Kontrolle: Alles andere sollte UNVERÄNDERT sein

### 🔍 Test-Schritte
- [ ] Filter anwenden (neuer Zeitraum) → Funktioniert
- [ ] "Filter zurücksetzen" Button → Funktioniert
- [ ] Charts laden (Pie-Charts, Bar-Charts, etc.) → Sichtbar
- [ ] "Netto-Sektor-Signal" → Chart erscheint
- [ ] "Market-Cap-Verteilung" → Chart erscheint
- [ ] "Top 5 Buys" Tabelle → Zeilen sichtbar
- [ ] "Top 5 Sells" Tabelle → Zeilen sichtbar
- [ ] Zur Trades gehen (Button) → Navigation funktioniert
- [ ] Trade-Detail öffnen (von Top 5) → Detail-Seite erscheint

### ❌ Falls Regression
```
Detail: Welche Funktionalität kaputt?
Ursache: Datei bei Edit fehlerhaft
Lösung: Git diff prüfen, bei Bedarf revert
```

---

## 🎯 Test 5: Trades-Arbeitsfläche & Unternehmen (Regression)

### ✅ Kontrolle: Sollte keine Änderungen geben

### 🔍 Quick-Navigation
- [ ] Öffne "Trades" Tab → Seite lädt
- [ ] Filtere Trades → Funktioniert
- [ ] "Einzeltrades anzeigen" / "Trades aggregieren" Toggle → Funktioniert
- [ ] Zeile auswählen → Aktionsbuttons erscheinen
- [ ] "Trade öffnen" → Detail-Seite wird angezeigt
- [ ] Zurück zur Listen-Übersicht → Funktioniert

- [ ] Öffne "Unternehmen" Tab → Seite lädt
- [ ] Suche nach Unternehmen → Funktioniert
- [ ] Zeile auswählen → Aktionsbuttons erscheinen
- [ ] "Unternehmensdetails öffnen" → Detail-Seite wird angezeigt

### ❌ Falls Fehler
```
Symptom: Trades-Seite schwarz / Fehler sichtbar
Ursache: Unerwarteter Edit-Fehler in Dashboard-Service
Lösung: Nur dashboard_page.py und navigation.py waren betroffen,
        Trades-Page sollte unberührt sein
```

---

## 📊 Test-Ergebnis-Summary

### Test Balance Sheet
| # | Test | Status | Hinweise |
|---|---|---|---|
| 1 | KPI-Karten: 4 statt 5 | ✅ / ⚠️ / ❌ | _________ |
| 2 | Footer: kein Datenmodus | ✅ / ⚠️ / ❌ | _________ |
| 3 | Sidebar: keine Uni-Nachricht | ✅ / ⚠️ / ❌ | _________ |
| 4 | Dashboard Funktionen Regression | ✅ / ⚠️ / ❌ | _________ |
| 5 | Trades/Unternehmen Regression | ✅ / ⚠️ / ❌ | _________ |

### Gesamtresultat
- [ ] ✅ **BESTANDEN** – Alle 5 Tests erfolgreich
- [ ] ⚠️ **MIT ANMERKUNGEN** – Tests bestanden, aber Kleinigkeiten fallen auf
- [ ] ❌ **FEHLGESCHLAGEN** – Ein oder mehr Tests nicht bestanden

---

## 📝 Detaillierte Anmerkungen

### Falls Tests nicht bestanden:
```
Test #: ___
Problem Description:
___________________________________________________________________________

Zugehöriger Log/Error:
___________________________________________________________________________

Vermutete Ursache:
___________________________________________________________________________

Handlung:
[ ] Issue eröffnet
[ ] Developer benachrichtigt  
[ ] Gerevert
```

---

## 🔗 Referenzen

| Ressource | Link |
|---|---|
| Audit-Report | `AUDIT_FIXES_2026_04_28.md` |
| Changelog | `CHANGELOG_2026_04_28.md` |
| Verbesserungsplan | `IMPROVEMENT_ROADMAP_PHASE2.md` |
| Dashboard-Code | `src/ui/pages/dashboard_page.py` |
| Navigation-Code | `src/app/navigation.py` |

---

## ✅ Sign-Off

**Getestet von:** ____________________  
**Datum:** ____________________  
**Zeit (Stunden):** ____________________  
**Browser:** ☐ Chrome ☐ Firefox ☐ Safari ☐ Edge  
**Umgebung:** ☐ Production ☐ Staging ☐ Local  

**Gesamturteil:**
```
☐ Ready for Production
☐ Ready with Comments
☐ Needs Fixes
```

**Kommentar:**
___________________________________________________________________________
___________________________________________________________________________

---

## 📞 Support

**Bei Fragen:** Siehe `CHANGELOG_2026_04_28.md` Technical Details  
**Bei Bugs:** Öffne Issue mit Test-Nummer (#1-5) und Screenshots  
**Bei Unsicherheit:** Kontaktiere Development Team

---

**Version:** 1.0  
**Erstellt:** 28. April 2026  
**Gültig bis:** 30. April 2026 (vor DB-II Präsentation)

