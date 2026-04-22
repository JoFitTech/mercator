# Mercator Steuerungsskripte - Übersicht

Das Projekt nutzt drei Wrapper-Skripte, die auf derselben Steuerlogik basieren.

## Öffentliche Befehle

### Core
- `start`
- `stop`
- `restart`

### Public Share
- `share-start`
- `share-stop`
- `share-reset`

Hinweis: `stop` und `restart` stoppen den Share-Tunnel automatisch mit.

## Verfügbare Skripte

### `mercator.ps1` (PowerShell)
```powershell
.\mercator.ps1 start
.\mercator.ps1 stop
.\mercator.ps1 restart
.\mercator.ps1 share-start
.\mercator.ps1 share-stop
.\mercator.ps1 share-reset
```

### `mercator.bat` (cmd.exe)
```cmd
mercator.bat start
mercator.bat stop
mercator.bat restart
mercator.bat share-start
mercator.bat share-stop
mercator.bat share-reset
```

### `mercator` (Bash)
```bash
./mercator start
./mercator stop
./mercator restart
```

Einmalig ausführbar machen:
```bash
chmod +x mercator
```

## Plattform-Empfehlung

- Windows Standard: `mercator.bat`
- Windows PowerShell: `mercator.ps1`
- Linux/macOS/WSL: `./mercator`

## Fehlerbehebung

### "mercator: Befehl nicht gefunden" (Windows)
Nutze im Windows-Terminal `mercator.bat` oder `.\mercator.ps1`.

### "./mercator: permission denied" (Linux/macOS/WSL)
```bash
chmod +x mercator
```

### Start/Restart schlägt mit Port-Konflikt fehl
```powershell
.\mercator.ps1 stop
.\mercator.ps1 start
```





