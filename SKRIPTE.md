# Mercator Steuerungsskripte - Übersicht

Das Projekt nutzt **drei komplementäre Wrapper-Skripte**, um die PowerShell-Logik (`mercator.ps1`) auf verschiedenen Plattformen und Shells zugänglich zu machen.

## Verfügbare Skripte

### 1. `mercator.ps1` (PowerShell, Windows – Primär)
**Plattform:** Windows  
**Shell:** PowerShell (pwsh oder powershell.exe)  
**Verwendung:**
```powershell
.\mercator.ps1 start
.\mercator.ps1 status
.\mercator.ps1 logs
```

**Vorteile:**
- Direkter Zugriff auf die volle Logik
- Keine Umwandlungsschicht
- Native PowerShell-Features

---

### 2. `mercator.bat` (cmd.exe, Windows – Alternative)
**Plattform:** Windows  
**Shell:** cmd.exe (Windows Command Prompt)  
**Verwendung:**
```cmd
mercator.bat start
mercator.bat status
mercator.bat logs
```

**Zweck:**
- Für User, die lieber cmd.exe verwenden
- Einfacher direkter Aufruf ohne PowerShell-Ausführungsrichtlinien
- Batch-Wrapper, der `mercator.ps1` aufruft

---

### 3. `mercator` (Bash, Unix/Linux/WSL – Cross-Plattform)
**Plattform:** Linux, macOS, WSL, oder Windows (mit Bash verfügbar)  
**Shell:** bash  
**Verwendung:**
```bash
./mercator start
./mercator status
./mercator logs
```

**Voraussetzung:**
- Bash und PowerShell müssen verfügbar sein (für WSL oder WSL-Integration)
- Datei muss ausführbar sein:
  ```bash
  chmod +x mercator
  ```

**Zweck:**
- Unix-Standard-CLI-Erlebnis
- Kompatibilität mit Linux/macOS Developer-Workflows
- WSL-Integration

---

## Aktionen (alle Skripte)

Alle Skripte unterstützen die gleichen Aktionen:

| Aktion | Beschreibung |
|--------|-------------|
| `start` | Startet den Stack (Uni-DB bevorzugt, sonst lokal) |
| `stop` | Stoppt alle Container |
| `restart` | Startet Containers neu (mit Cleanup) |
| `status` | Zeigt Containerstatus an |
| `logs` | Streamt Logs (default: `app`) |
| `logs -Service mongo` | Logs eines spezifischen Services |
| `init-db` | Initialisiert MySQL-Schema |
| `doctor` | Führt Schema-Check durch |
| `open` | Öffnet App im Browser |
| `cleanup` | Entfernt verwaiste Container |
| `e2e-install` | Installiert E2E-Abhängigkeiten |
| `e2e-smoke` | Führt Smoke-Tests durch |
| `e2e` | Führt komplette E2E-Suite durch |

---

## Empfehlungen nach Plattform

### Windows Benutzer (Standard Terminal / cmd.exe)
**Im normalen Terminal ist Bash nicht verfügbar.**

1. **Empfohlen:** `mercator.bat start` (einfachste Methode)
2. **Alternative:** `.\mercator.ps1 start` (wenn PowerShell bevorzugt)

```cmd
REM Im cmd.exe / Normal Terminal
mercator.bat start
mercator.bat status
mercator.bat logs
```

oder in PowerShell:
```powershell
.\mercator.ps1 start
.\mercator.ps1 status
.\mercator.ps1 logs
```

### Windows + Git Bash / WSL
Wenn du **Git Bash oder WSL** installiert hast, kannst du auch `./mercator` verwenden:

```bash
./mercator start
./mercator status
```

Das Bash-Skript erkennt automatisch, ob PowerShell verfügbar ist.

### macOS / Linux Benutzer
**Empfohlen:** `mercator` (Standard Bash)

```bash
./mercator start
```

### WSL Benutzer (Windows mit Linux-Subsystem)
**Empfohlen:** `mercator` (Bash) oder PowerShell

```bash
# Bash im WSL
./mercator start

# oder PowerShell
pwsh -File mercator.ps1 -Action start
```

---

## Technische Details

### mercator.bat
- Wrapper in cmd.exe-Syntax
- Ruft `powershell.exe -NoProfile -File mercator.ps1` auf
- Einfaches Argument-Passing

### mercator (Bash)
- Wrapper in bash-Syntax
- Erkennt verfügbare PowerShell (`pwsh` oder `powershell`)
- Ruft das Bash-Skript auf: `pwsh -NoProfile -File mercator.ps1`
- Benötigt PowerShell als Backend (für Docker-Kommandos)

### mercator.ps1
- Die **Haupt-Implementierung**
- Enthält alle Geschäftslogik (DB-Checks, Container-Management, Konfiguration)
- Die anderen Skripte sind reine Wrapper

---

## Git-Attribute

Alle Skripte sind in `.gitattributes` konfiguriert:
- **mercator** und Shell-Scripts: Unix line endings (`LF`)
- **mercator.bat** und PowerShell: Windows line endings (`CRLF`)
- **mercator.ps1**: Windows line endings (`CRLF`)

Dies gewährleistet korrekte Zeilenumbrüche auf allen Plattformen.

---

## Fehlerbehebung

### "mercator: Befehl nicht gefunden" (Windows)
**Im normalen Windows Terminal** existiert das Bash-Skript `./mercator` nicht oder kann nicht ausgeführt werden.

**Lösung:** Verwende `mercator.bat` oder `.\mercator.ps1` stattdessen:
```cmd
mercator.bat start
```

oder

```powershell
.\mercator.ps1 start
```

### "mercator.bat: Befehl nicht gefunden" (Git Bash / WSL)
**Im WSL oder Git Bash** existiert `.bat` Datei nicht als ausführbares Skript.

**Lösung:** Verwende `./mercator` stattdessen:
```bash
./mercator start
```

### "./mercator: permission denied" (Linux/macOS/WSL)
Die Bash-Datei hat keine Ausführungsberechtigung.

**Lösung:** Mache die Datei ausführbar:
```bash
chmod +x mercator
./mercator start
```

### "PowerShell nicht gefunden" (Bash-Skript)
Das `./mercator` Bash-Skript benötigt PowerShell als Backend.

**Lösungen:**
1. Installiere PowerShell: https://github.com/PowerShell/PowerShell/releases
2. Oder verwende auf Windows direkt: `mercator.bat start`
3. Auf Linux/macOS: Installiere PowerShell oder nutze das Python CLI (falls vorhanden)

### "ExitCode 1" beim Start
Container-Konflikte oder Port-Probleme.

**Lösung:**
```powershell
.\mercator.ps1 cleanup
.\mercator.ps1 start
```

oder mit Bash:
```bash
./mercator cleanup
./mercator start
```

---

---

## Zusammenfassung

| Datei | Plattform | Shell | Wann verwenden | Status |
|-------|-----------|-------|---|--------|
| `mercator.bat` | Windows (Standard) | cmd.exe | **Windows Normal Terminal** | ✅ **Empfohlen** |
| `mercator.ps1` | Windows | PowerShell | Windows PowerShell oder pwsh | ✅ Verfügbar |
| `mercator` | Linux/macOS/WSL | Bash | **macOS, Linux, WSL** | ✅ **Empfohlen** |

**Faustregel:**
- **Windows Standard:** `mercator.bat start`
- **macOS / Linux:** `./mercator start`
- **Windows + Git Bash/WSL:** `./mercator start` oder `mercator.bat start`

Alle Varianten verweisen auf die gleiche PowerShell-Implementierung (`mercator.ps1`)!




