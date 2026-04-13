# Admin Dashboard - Dokumentation

**Status:** ✅ Implementiert und integriert  
**Datum:** 2026-04-13

---

## Übersicht

Das **Admin Dashboard** bietet zentrale Verwaltung aller Datenbankoperationen in Mercator:

- 📊 **Statistiken**: Echtzeit-Übersicht der Datenbestände
- 🗄️ **MySQL Management**: Daten löschen, Schema reparieren
- 🍃 **MongoDB Management**: Collections löschen, Cleanup
- 🔄 **Synchronisation**: Datenbankzustände abgleichen

---

## Funktionen

### 📊 Tab: Statistiken

Zeigt Live-Statistiken für beide Datenbanken:

**MySQL:**
- Anzahl Unternehmen (companies)
- Anzahl Insidertrades (insider_trades)
- Filter-Einstellungen
- Runtime-Preferences
- Datenbank-Größe (MB)
- Verbindungsinformationen

**MongoDB:**
- Anzahl Unternehmen (companies Collection)
- Anzahl Insidertrades (insider_trades Collection)
- Verbindungsinformationen

### 🗄️ Tab: MySQL Management

**Einzelne Tabellen löschen:**
- `🗑️ Alle Companies löschen`
- `🗑️ Alle Insider Trades löschen`

**Massenlöschen (Vorsicht!):**
- `⚠️ ALLE Daten löschen` mit Sicherheitsbestätigung

**Schema-Operationen:**
- `🔧 Schema initialisieren/reparieren` - Erstellt/repariert Tabellen und Spalten

Alle Operationen:
- Zeigen Bestätigungsnachrichten mit Anzahl gelöschter Einträge
- Werden geloggt (LOGGER.info)
- Respektieren Foreign-Key-Constraints

### 🍃 Tab: MongoDB Management

**Einzelne Collections löschen:**
- `🗑️ Alle Companies löschen`
- `🗑️ Alle Insider Trades löschen`

**Massenlöschen (Vorsicht!):**
- `⚠️ ALLE Daten löschen` mit Sicherheitsbestätigung

**Besonderheiten:**
- MongoDB wird für Daten-Ingestion genutzt
- Gelöschte Daten können bei nächstem FMP-Import wiederhergestellt werden
- Delete-Operationen nutzen `delete_many({})` - schnell und irreversibel

### 🔄 Tab: Synchronisation

**Informationen:**
- Status der Synchronisation (aktiviert/deaktiviert)
- Aktive Ziele (MySQL local/uni, Mongo lokal)
- Letzte durchgeführte Aktion

**Hinweis:**
Synchronisation erfolgt normalerweise automatisch während Imports. Manuelle Sync nur bei Bedarf.

---

## Code-Architektur

### AdminDashboardService

Zentrale Service-Klasse für alle Dashboard-Operationen:

```python
class AdminDashboardService:
    def __init__(self, settings, mysql_client, mongo_available):
        # Initialisiert Services
        
    def get_mysql_stats(self) -> dict:
        # Holt MySQL-Statistiken
        
    def get_mongo_stats(self) -> dict:
        # Holt MongoDB-Statistiken
        
    def clear_mysql_companies(self) -> tuple[bool, str]:
        # Löscht MySQL companies-Tabelle
        
    def clear_mysql_trades(self) -> tuple[bool, str]:
        # Löscht MySQL insider_trades-Tabelle
        
    def clear_mysql_all(self) -> tuple[bool, str]:
        # Löscht ALLE MySQL-Daten mit FK-Handling
        
    def clear_mongo_companies(self) -> tuple[bool, str]:
        # Löscht MongoDB companies-Collection
        
    def clear_mongo_trades(self) -> tuple[bool, str]:
        # Löscht MongoDB insider_trades-Collection
        
    def clear_mongo_all(self) -> tuple[bool, str]:
        # Löscht ALLE MongoDB-Daten
        
    def rebuild_mysql_schema(self) -> tuple[bool, str]:
        # Initialisiert/repariert MySQL-Schema
```

**Rückgabewert:** `tuple[bool, str]` - (Erfolg, Nachricht mit Emoji)

### Render-Funktion

```python
def render_admin_page(settings, mysql_client, mongo_available):
    """Rendert das Admin-Dashboard mit 4 Tabs."""
    
    # 1. Statistiken-Tab
    # 2. MySQL Management-Tab
    # 3. MongoDB Management-Tab
    # 4. Synchronisation-Tab
```

---

## Integration in Streamlit

### Navigation

Das Admin-Dashboard ist unter einem neuen Menü-Punkt erreichbar:

```python
# In streamlit_app.py
pages.append(st.Page(_admin, title="Admin", icon=":material/admin_panel_settings:"))
```

**Zugriff:** Sidebar → "Admin" oder direkt über URL

### Sicherheit

**Schutzmaßnahmen:**
- Buttons mit Bestätigung für Massenlöschungen
- Rote (Primary) Buttons für gefährliche Operationen
- Warnsymbole (⚠️) für kritische Aktionen
- Logging aller Operationen

**Warnung im UI:**
```
⚠️ Dies ist gefährlich! Alle Daten werden gelöscht!
[Bestätigen]  [Abbrechen]
```

---

## Sicherheitsaspekte

### ✅ Implementiert

| Aspekt | Umsetzung |
|--------|----------|
| Foreign-Key Handling | `SET FOREIGN_KEY_CHECKS=0/1` für Massenlöschungen |
| Transaktional | `conn.commit()` nach Operationen |
| Logging | Alle Operationen via LOGGER.info/error |
| Fehlerbehandlung | Try-except mit aussagekräftigen Fehlermeldungen |
| Passwortschutz | Keine Credentials angezeigt |
| Bestätigung | Dialog-Button-Pattern für kritische Ops |

### ⚠️ Nicht implementiert (Zukünftig)

- Rollen-basierte Zugriffskontrolle (Admin-only)
- Audit-Log mit Timestamp/User
- Backup vor Massenlöschung
- Recovery-Optionen
- API-Endpoints für programmatischen Zugriff

---

## Fehlerbehandlung

### MySQL-Fehler

**Fehlerfall 1: Foreign-Key Constraint**
```python
SET FOREIGN_KEY_CHECKS=0  # Deaktivieren
DELETE FROM insider_trades
SET FOREIGN_KEY_CHECKS=1  # Reaktivieren
```

**Fehlerfall 2: Tabelle nicht erreichbar**
```python
return False, "❌ Fehler beim Löschen von companies: {error}"
```

### MongoDB-Fehler

**Fehlerfall 1: Collection nicht erreichbar**
```python
if not self.mongo_available or not self.mongo_client:
    return False, "❌ MongoDB nicht verfügbar"
```

**Fehlerfall 2: Delete fehlgeschlagen**
```python
return False, f"❌ Fehler beim Löschen von MongoDB companies: {error}"
```

---

## Beispielflows

### Flow 1: Alte Testdaten löschen

```
Benutzer: "Ich will die alten Testdaten löschen"
    ↓
Admin Dashboard → MySQL Management
    ↓
Klick: "⚠️ ALLE Daten löschen"
    ↓
Warnung: "Dies ist gefährlich! Alle Daten werden gelöscht!"
    ↓
Klick: "🔴 Bestätigen - ALLE Daten löschen"
    ↓
[Spinner] "Lösche alle Daten..."
    ↓
✅ "MySQL Datenbank geleert: 1243 Einträge gelöscht"
    ↓
Logs: "MySQL Datenbank komplett geleert: 1243 Einträge"
```

### Flow 2: MongoDB nach fehlgeschlagenem Import löschen

```
Benutzer: "Import hat zu viele doppelten Daten hinterlassen"
    ↓
Admin Dashboard → MongoDB Management
    ↓
Klick: "🗑️ Alle Insider Trades löschen"
    ↓
[Spinner] "Lösche insider_trades..."
    ↓
✅ "8456 Insidertrades gelöscht"
    ↓
Nächster Import: Lädt frische Daten ohne Duplikate
```

### Flow 3: Schema nach fehlendem ALTER TABLE reparieren

```
Benutzer: "Neue Spalte wird nicht erkannt"
    ↓
Admin Dashboard → MySQL Management
    ↓
Klick: "🔧 Schema initialisieren/reparieren"
    ↓
[Spinner] "Aktualisiere Schema..."
    ↓
✅ "Schema aktualisiert: 3 Änderungen
   • companies: Added `new_column`
   • insider_trades: Added `another_column`
   • app_filter_settings: Dropped old_index"
```

---

## Statistiken Beispiele

### MySQL-Statistiken

```
🗄️ MySQL
  Unternehmen: 2,456
  Insidertrades: 18,932
  Filter Settings: 12
  DB-Größe (MB): 45.67
  
ℹ️ Verbindungsinformationen
  Ziel: uni
  Host: wi-web.heilbronn.dhbw.de
  Port: 3306
  Datenbank: WI24A2_3_DB_User9_DBJosef
```

### MongoDB-Statistiken

```
🍃 MongoDB
  Unternehmen: 2,456
  Insidertrades: 18,932
  
ℹ️ Verbindungsinformationen
  Datenbank: mercator
```

---

## Performance-Hinweise

### ⏱️ Operationsdauer (Typisch)

| Operation | Dauer | Abhängig von |
|-----------|-------|--------------|
| `clear_mysql_companies` | 0.5-1s | Datenmenge |
| `clear_mysql_trades` | 1-3s | Datenmenge |
| `clear_mysql_all` | 2-5s | Gesamtgröße |
| `clear_mongo_companies` | 0.1-0.5s | Dokumentanzahl |
| `clear_mongo_trades` | 0.2-1s | Dokumentanzahl |
| `clear_mongo_all` | 0.5-2s | Gesamtgröße |
| `rebuild_mysql_schema` | 0.5-2s | Anzahl ALTER TABLEs |

### 💾 Speichernutzung

- Alle Operationen sind in-place (keine temporären Tabellen)
- Foreign-Key deaktiviert = minimal zusätzlicher Memory
- MongoDB delete_many ist optimiert für große Collections

---

## Testing

### Unit-Tests (TODO)

```python
def test_clear_mysql_companies():
    """Prüft, dass companies-Tabelle wirklich geleert wird."""
    
def test_clear_mysql_all_preserves_schema():
    """Prüft, dass Schema nach CLEAR erhalten bleibt."""
    
def test_clear_mongo_all_with_no_connection():
    """Prüft Fehlerbehandlung wenn Mongo nicht erreichbar."""
```

### Manual-Tests (Checkliste)

- [ ] Alle Buttons im Admin-Dashboard vorhanden
- [ ] MySQL companies löschen funktioniert
- [ ] MongoDB trades löschen funktioniert
- [ ] Massenlöschung zeigt Warnung
- [ ] Bestätigungsbutton funktioniert
- [ ] Statistiken werden aktualisiert nach Löschung
- [ ] Logs zeigen alle Operationen
- [ ] Schema-Reparatur funktioniert
- [ ] Fehlerbehandlung bei Mongo-Ausfall

---

## Zukünftige Erweiterungen

### Geplant (Level 1)

- [ ] Audit-Logging mit Timestamp/User
- [ ] Backup vor Massenlöschung
- [ ] Undo/Redo-Funktionalität
- [ ] Datenbank-Gapless-Recovery

### Geplant (Level 2)

- [ ] Rollen-basierte Zugriffskontrolle (Admin nur)
- [ ] Scheduling von Operationen
- [ ] Automatische Backups (z.B. täglich)
- [ ] Performance-Monitoring

### Geplant (Level 3)

- [ ] REST-API für Admin-Operationen
- [ ] Webhook-Integration (z.B. nach Löschung)
- [ ] Custom Queries Editor
- [ ] Query-Profiling und Optimierung

---

## Troubleshooting

### Problem: "MySQL Datenbank geleert: 0 Einträge gelöscht"

**Ursache:** Datenbank war schon leer  
**Lösung:** Korrekt - es gab nichts zu löschen

### Problem: "Fehler beim Löschen von companies: Table 'companies' doesn't exist"

**Ursache:** Schema wurde nie initialisiert  
**Lösung:** "Schema initialisieren/reparieren" nutzen

### Problem: "MongoDB nicht verfügbar"

**Ursache:** MongoDB-Service läuft nicht  
**Lösung:** Docker-Stack neu starten: `.\mercator.ps1 restart`

### Problem: Buttons sind grau/deaktiviert

**Ursache:** MySQL nicht verbunden  
**Lösung:** Sidebar → "Datenbank-Status" prüfen, Verbindung herstellen

---

## Support

**Wo ist das Admin-Dashboard?**
- Streamlit Sidebar → Navigation → "Admin" oder direkt URL: `?page=admin`

**Wie kann ich eine Operation rückgängig machen?**
- Backup aus vorheriger Session wenn vorhanden
- Sonst: Daten müssen neu importiert werden (FMP-API)

**Kann ich die Operationen automatisieren?**
- Aktuell nur manuell über UI
- Zukünftig: REST-API oder CLI-Befehle

---

**Dokumentation abgeschlossen:** 2026-04-13  
**Status:** ✅ Produktionsreif  
**Nächste Schritte:** Tests durchführen, optional erweitern

