# Quick Reference - Mercator Steuerung

## Erlaubte Befehle

Es gibt nur noch diese Kommandos:

- `start`
- `stop`
- `restart`
- `share-start`
- `share-stop`
- `share-reset`

## Welches Skript für welche Situation?

### 🪟 Windows (cmd.exe)
```cmd
mercator.bat start
mercator.bat stop
mercator.bat restart
mercator.bat share-start
mercator.bat share-stop
mercator.bat share-reset
```

### 💻 Windows (PowerShell)
```powershell
.\mercator.ps1 start
.\mercator.ps1 stop
.\mercator.ps1 restart
.\mercator.ps1 share-start
.\mercator.ps1 share-stop
.\mercator.ps1 share-reset
```

### 🐧 Linux/macOS/WSL (Bash)
```bash
./mercator start
./mercator stop
./mercator restart
```

Vorher einmalig:
```bash
chmod +x mercator
```

Hinweis: Die `share-*` Befehle laufen über `mercator.ps1`/`mercator.bat`.

## Häufige Szenarien

### App normal starten/stoppen
```cmd
mercator.bat start
mercator.bat stop
```

### Stack neu starten
```cmd
mercator.bat restart
```

### Public Share neu initialisieren
```cmd
mercator.bat share-reset
```

