# Import-Service Fehlerbehebung

## Problem: "Import-Service nicht verfügbar. Rohdatenspeicherung ist derzeit deaktiviert"

Dieser Fehler tritt auf, wenn der FMP (Financial Modeling Prep) API-Key ungültig oder nicht konfiguriert ist.

---

## Schnelllösung (3 Schritte)

### 1. API-Key besorgen
Erhalte einen kostenlosen oder bezahlten API-Key auf:
```
https://financialmodelingprep.com/
```

### 2. API-Key konfigurieren (eine der folgenden Methoden)

#### Methode A: Umgebungsvariable (empfohlen für Production)
```bash
# Windows PowerShell
$env:FMP_API_KEY = "your_actual_api_key"

# Linux/Mac (Bash)
export FMP_API_KEY="your_actual_api_key"
```

#### Methode B: .env-Datei (empfohlen für Entwicklung)
```bash
# 1. Kopiere die Vorlage
cp .env.example .env

# 2. Bearbeite .env und ersetze:
FMP_API_KEY=your_actual_api_key_here
```

#### Methode C: Streamlit Secrets (für Streamlit Cloud)
```bash
# Erstelle oder bearbeite: .streamlit/secrets.toml
FMP_API_KEY = "your_actual_api_key"
```

### 3. App neu starten
```bash
streamlit run streamlit_app.py
```

---

## Validierung

Nach der Konfiguration siehst du beim Start:
```
✅ ImportService aktiviert
✅ Rohdatenspeicherung verfügbar
```

Statt:
```
❌ ImportService nicht verfügbar. Rohdatenspeicherung ist derzeit deaktiviert.
⚠️  FMP-Konfiguration ungueltig (env): FMP_API_KEY fehlt oder ist ein Platzhalter.
```

---

## Häufige Fehler

### Fehler 1: API-Key ist ein Platzhalter
**Zeichen:** Der Fehler erwähnt `FMP_API_KEY ist ein Platzhalter`
**Lösung:** Ersetze den Platzhalter in .env durch deinen echten API-Key

**Ungültige Werte (Platzhalter):**
- `change_me`
- `your_api_key`
- `demo`
- `placeholder`
- `null`
- (leer)

**Gültige Werte:**
- `sk_p1234567890abcdef1234567890`
- Jeder Key von https://financialmodelingprep.com/

### Fehler 2: FMP_API_KEY_ENVIRONMENT_VARIABLE nicht gesetzt
**Ursache:** Kein API-Key in ENV, .env oder Streamlit Secrets gesetzt
**Lösung:** Führe Schritt 2 oben durch (konfiguriere den API-Key)

### Fehler 3: Andere FMP-Client-Fehler
**Zeichen:** "FMP-Client Initialisierung fehlgeschlagen"
**Lösungen:**
1. Prüfe, ob dein API-Key noch gültig ist (evtl. abgelaufen oder deaktiviert)
2. Prüfe die FMP API Status: https://status.financialmodelingprep.com/
3. Prüfe deine Internetverbindung
4. Prüfe die FMP Rate Limits (kostenlose Keys haben Limits)

---

## Technische Details

### Wie der Import-Service initialisiert wird

1. **Umgebung laden** → `load_settings()` in `src/config/settings.py`
   - Liest `FMP_API_KEY` aus ENV, .env oder Streamlit Secrets

2. **Validierung** → `validate_fmp_api_key()` in `src/config/settings.py`
   - Prüft, ob der Key nicht leer ist
   - Prüft, ob der Key kein Platzhalter ist
   - Wirft `ValueError` bei ungültigem Key

3. **FMP-Client erstellen** → `FmpClient.__init__()` in `src/data_sources/fmp_client.py`
   - Ruft `validate_fmp_api_key()` auf
   - Kann `ValueError` werfen

4. **Import-Service erstellen** → `ServiceFactory.build_all()` in `src/services/factory.py`
   - Fängt `ValueError` ab
   - Setzt `ServiceFactory.last_import_issue` mit Fehlermeldung
   - Protokolliert die Fehlermeldung in den Logs

5. **UI zeigt Status** → `streamlit_app.py`
   - Zeigt `ServiceFactory.last_import_issue` bei fehlender Aktivierung

### Debugging

**Log-Ausgabe ansehen:**
```bash
# Starten mit Debug-Logs
streamlit run streamlit_app.py --logger.level=debug
```

**Getestete Pfade:**
- ✅ FMP_API_KEY als Umgebungsvariable
- ✅ FMP_API_KEY in .env
- ✅ FMP_API_KEY in Streamlit Secrets
- ✅ Platzhalter werden erkannt und abgelehnt
- ✅ Leer/Null werden erkannt und abgelehnt

---

## Support

Falls der Fehler weiterhin auftritt:

1. **Prüfe die .env-Datei:**
   ```bash
   cat .env | grep FMP_API_KEY
   ```

2. **Prüfe die Umgebungsvariable:**
   ```bash
   # Windows PowerShell
   echo $env:FMP_API_KEY
   
   # Linux/Mac Bash
   echo $FMP_API_KEY
   ```

3. **Prüfe die Streamlit-Secrets:**
   ```bash
   cat .streamlit/secrets.toml | grep FMP_API_KEY
   ```

4. **Prüfe die Logs:**
   ```bash
   streamlit run streamlit_app.py --logger.level=debug 2>&1 | grep -i fmp
   ```

5. **Starte die App neu nach Änderungen** (Streamlit lädt .env nur beim Start)

---

## Weitere Ressourcen

- **FMP API Dokumentation:** https://financialmodelingprep.com/api/documentation
- **Streamlit Secrets Dokumentation:** https://docs.streamlit.io/develop/concepts/connections/secrets-management
- **Mercator README:** https://github.com/...

