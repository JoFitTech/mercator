# Docker Rebuild & cloudflared-Installation Guide

## Problem

Nach Git-Updates fehlt den Nutzern häufig `cloudflared` in ihrem App-Container, weil die Start-Skripte standardmäßig kein Rebuild erzwingen. Das führt zu fehlgeschlagenen Public-Share-Initialisierungen.

### Ursachen

1. **`docker compose up -d`** ohne `--build` nutzt gecachten Images ohne Dockerfile-Änderungen
2. Nutzer müssen manuell `--build` hinzufügen, was oft vergessen wird
3. Keine Diagnostik, um das fehlende Binary zu identifizieren

## Lösung

### 1. Automatisches Rebuild in Startskripten

**Betroffene Dateien:**
- `mercator.ps1` (PowerShell für Windows)
- `mercator.bat` (Batch-Wrapper)
- `mercator` (Bash für Linux/macOS)

**Änderungen:**
- `start` und `restart` verwenden jetzt standardmäßig `--build`
- Der Rebuild wird nur durchgeführt, wenn Dockerfile oder Dependencies sich geändert haben (Docker verwaltet das intelligent)
- Kein Overhead wenn Code-Only-Changes erfolgt sind

**Beispiel:**
```powershell
# VORHER
Invoke-ComposeQuiet up -d --wait

# NACHHER
Invoke-ComposeQuiet up -d --build --wait
```

### 2. Preflight-Checks im Tunnel-Service

**`src/services/public_share_service.py`**

Neue Preflight-Checks vor Tunnel-Start:

1. **Binary-Verfügbarkeit**: Prüft ob `cloudflared` im System verfügbar ist
2. **Lokale URL-Erreichbarkeit**: Prüft ob Streamlit auf dem konfigurierten Port läuft

**Fehlermeldungen sind jetzt eindeutig:**
- ❌ Binary fehlt → Deutlicher Hinweis auf Installation/Rebuild
- ❌ Lokale App nicht erreichbar → Hinweis, dass Streamlit nicht läuft
- ✅ Beides OK → Tunnel wird gestartet

### 3. Verbesserte Diagnostik

**Admin-UI (Public Share Tab):**

Zeigt jetzt:
- Konfigurierter Binary-Pfad
- Aufgelöster tatsächlicher Binary-Pfad (falls vorhanden)
- `cloudflared --version` Output
- Deutliche Fehlermeldung, wenn Binary nicht gefunden wird
- Vorschlag zum Rebuild bei fehlender Binary

**Diagnostik-Methode:**
```python
provider.get_binary_diagnostics()
# Gibt zurück:
# {
#     "configured_bin": "cloudflared",
#     "resolved_bin_path": "/usr/local/bin/cloudflared",
#     "binary_available": "Ja",
#     "version": "cloudflared version 1.5.0"
# }
```

### 4. Health-Check-Verbesserungen

**Problem:** Die öffentliche Tunnel-URL konnte von localhost nicht getestet werden (DNS/Netzwerk-Abstraktionen)

**Lösung:** Health-Check nutzt jetzt die **lokale URL** statt öffentliche URL

- ✅ Zuverlässiger (keine Netzwerk-Routing-Probleme)
- ✅ Schneller (keine externen HTTP-Requests)
- ✅ Funktioniert auch ohne Internetverbindung zum Contentserver

## Nutzung

### Normale Nutzung (alles automatisch)

```bash
# Alle Start-Varianten verwenden jetzt --build automatisch
./mercator start
./mercator restart
```

Auf Windows:
```powershell
.\mercator.ps1 start
.\mercator.ps1 restart
```

### Manueller Force-Rebuild (wenn nötig)

Falls Sie trotzdem ein manuelles Rebuild erzwingen wollen:

```bash
# Expliziter Rebuild
docker compose -f mercator-compose.yml down
docker compose -f mercator-compose.yml up -d --build
```

## Dockerfile (für Kontext)

```dockerfile
# cloudflared wird geladen
RUN curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o /usr/local/bin/cloudflared \
    && chmod +x /usr/local/bin/cloudflared \
    && cloudflared --version
```

**Installation passiert automatisch mit dem Rebuild.**

## Konfiguration (.env)

```env
# Neu in .env.example dokumentiert:
ENABLE_PUBLIC_SHARE=false                              # Feature aktivieren?
PUBLIC_SHARE_PROVIDER=cloudflare                       # Provider (aktuell nur cloudflare)
PUBLIC_SHARE_LOCAL_URL=http://localhost:8501           # Lokale Streamlit URL
CLOUDFLARED_BIN=cloudflared                            # Binary-Name/Pfad
PUBLIC_SHARE_STARTUP_TIMEOUT_SECONDS=20                # Timeout für Tunnel-Start
PUBLIC_SHARE_HEALTHCHECK_TIMEOUT_SECONDS=2.0           # Timeout für Health-Checks
```

## Fehlerbehandlung

### Fehlerfall: `cloudflared nicht gefunden`

**Ursache:** Alte Image oder Rebuild nicht durchgeführt

**Lösung:**
```bash
# Option 1: Start-Skript nutzt --build automatisch
./mercator restart

# Option 2: Manuell forcer
docker compose -f mercator-compose.yml down
docker compose -f mercator-compose.yml up -d --build
```

### Fehlerfall: `Lokale URL nicht erreichbar`

**Ursache:** Streamlit läuft nicht

**Lösung:**
```bash
# Stelle sicher, dass die App läuft
./mercator start

# Oder starte explizit den App-Container
docker compose -f mercator-compose.yml up -d app
```

## Tests

Neue/Erweiterte Tests in `tests/test_public_share_service.py`:

- ✅ Binary-Diagnostik bei fehlendem Binary
- ✅ Preflight-Check schlägt bei unreachbarer lokaler URL fehl
- ✅ Health-Check nutzt lokale URL (nicht öffentliche)
- ✅ Korrekter Status-Übergang bei erfolgreicher lokaler URL

```bash
# Tests durchführen
./mercator e2e-install
./mercator e2e-smoke  # oder pytest tests/test_public_share_service.py
```

## Zusammenfassung der Änderungen

| Feature | Dateien | Effekt |
|---------|---------|--------|
| Auto-Build | mercator.ps1, mercator, mercator.bat | `--build` standardmäßig bei start/restart |
| Preflight-Checks | public_share_service.py | Binary + lokale URL vor Tunnel-Start prüfen |
| Bessere Diagnostik | admin_page.py, public_share_service.py | Binary-Version, aufgelöster Pfad, klare Fehler |
| Health-Check Verbesserung | public_share_service.py | Lokale URL statt öffentliche URL |
| Dokumentation | .env.example | Public Share Variablen dokumentieren |
| Tests | test_public_share_service.py | Erweiterte Test-Abdeckung |

## Für Entwickler

### Integration in bestehenden Code

```python
from src.services.public_share_service import CloudflareQuickTunnelProvider

provider = CloudflareQuickTunnelProvider()

# Diagnostik abrufen
diags = provider.get_binary_diagnostics()
print(f"Binary available: {diags['binary_available']}")
print(f"Version: {diags['version']}")

# Tunnel starten (mit Preflight-Checks)
session = provider.start("http://localhost:8501")
if session.status == TunnelStatus.ERROR:
    print(f"Fehler: {session.error_message}")
```

### Kommende Verbesserungen

- [ ] HealthCheck mit exponentieller Backoff bei wiederholten Fehlern
- [ ] Automatische Service-Restart-Versuche bei transienten Fehlern
- [ ] Metriken (erfolgreiche Tunnels, durchschnittliche Startzeit)
- [ ] Support für weitere Provider (z.B. ngrok, Tailscale)

