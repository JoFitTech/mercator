# Quick Reference - Mercator Steuerung

## Welches Skript für welche Situation?

### 🪟 Ich bin auf Windows und verwende das normale Terminal/cmd.exe
```cmd
mercator.bat start
mercator.bat status
mercator.bat logs
mercator.bat open
```
✅ **Das ist die einfachste Methode für Windows-User!**

---

### 💻 Ich bin auf Windows und verwende PowerShell
```powershell
.\mercator.ps1 start
.\mercator.ps1 status
.\mercator.ps1 logs
.\mercator.ps1 open
```

---

### 🐧 Ich bin auf Linux oder macOS
```bash
./mercator start
./mercator status
./mercator logs
./mercator open
```
Vorher einmalig:
```bash
chmod +x mercator
```

---

### 🔵 Ich bin auf Windows mit Git Bash oder WSL
```bash
./mercator start           # Bash-Skript
# oder
cmd /c mercator.bat start  # Batch-Skript
```

---

## Alle verfügbaren Befehle

```
mercator.bat start              # Startet den kompletten Stack
mercator.bat stop               # Stoppt alle Container
mercator.bat restart            # Startet neu (mit Cleanup)
mercator.bat status             # Zeigt Container-Status
mercator.bat logs               # Streamt Live-Logs (default: app)
mercator.bat logs -Service mongo # Logs eines spezifischen Services
mercator.bat init-db            # Initialisiert MySQL-Schema
mercator.bat doctor             # Führt Schema-Check durch
mercator.bat open               # Öffnet die App im Browser
mercator.bat cleanup            # Entfernt alte Container
mercator.bat e2e-install        # Installiert E2E-Tests
mercator.bat e2e-smoke          # Schnelle E2E-Tests
mercator.bat e2e                # Komplette E2E-Test-Suite
```

Gleiche Befehle für `./mercator` (Bash) oder `.\mercator.ps1` (PowerShell)

---

## Häufige Szenarien

### App starten
```cmd
mercator.bat start
mercator.bat open
```

### Container gestoppt, neu starten
```cmd
mercator.bat restart
```

### Alte Container aufräumen
```cmd
mercator.bat cleanup
mercator.bat start
```

### Live-Logs ansehen
```cmd
mercator.bat logs          # App-Logs
mercator.bat logs app      # App-Logs (explizit)
mercator.bat logs mongo    # MongoDB-Logs
mercator.bat logs mysql    # MySQL-Logs
```

### Datenbank initialisieren
```cmd
mercator.bat init-db
```

### Tests starten (nach E2E-Setup)
```cmd
mercator.bat e2e-install   # Nur einmalig
mercator.bat e2e-smoke     # Schnelle Tests
mercator.bat e2e           # Alle Tests
```

---

## Fehlerbehandlung

| Problem | Lösung |
|---------|--------|
| "Port bereits in Verwendung" | `mercator.bat cleanup` dann `mercator.bat start` |
| App startet nicht | `mercator.bat logs` + `mercator.bat doctor` |
| Docker nicht erreichbar | Stelle sicher, dass Docker Desktop läuft |
| Alte Container stören | `mercator.bat cleanup` |

---

## PowerShell vs cmd.exe vs Bash

- **cmd.exe / mercator.bat**: Windows Standard, keine Umwandlung nötig
- **PowerShell / mercator.ps1**: Volle PowerShell-Features, etwas komplexer
- **Bash / mercator**: Cross-Plattform, für Linux/macOS/WSL Standard

**Für Windows-Anfänger:** `mercator.bat` ist am einfachsten! ✅

