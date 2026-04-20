# Stabiler Tunnel-Launcher mit Retry-Logik und aktiven Health-Checks
param(
    [int]$Port = 8501,
    [int]$MaxRetries = 5,
    [int]$RetryDelaySeconds = 10
)

$ErrorActionPreference = "Continue"
$cloudflaredPath = "C:\Users\josef.lautner\PycharmProjects\mercator\cloudflared.exe"
$logFile = "C:\Users\josef.lautner\PycharmProjects\mercator\tunnel_launcher.log"
$tunnelUrlFile = "C:\Users\josef.lautner\PycharmProjects\mercator\TUNNEL_URL.txt"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp | $Message" | Tee-Object -FilePath $logFile -Append
}

function Test-AppReachable {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Extract-TunnelUrl {
    param([string]$LogContent)
    $matches = [regex]::Matches($LogContent, 'https://[a-z\-]+\.trycloudflare\.com')
    if ($matches.Count -gt 0) {
        return $matches[0].Value
    }
    return $null
}

Write-Log "=========================================="
Write-Log "TUNNEL LAUNCHER GESTARTET"
Write-Log "=========================================="
Write-Log "Ziel: http://127.0.0.1:$Port"
Write-Log "cloudflared: $cloudflaredPath"

# Stelle sicher, dass alte Prozesse weg sind
Write-Log "Beende alte cloudflared Prozesse..."
taskkill /IM cloudflared.exe /F 2>&1 | Out-Null
Start-Sleep -Seconds 2

$retryCount = 0
$tunnelUrl = $null

while ($retryCount -lt $MaxRetries -and -not $tunnelUrl) {
    $retryCount++
    Write-Log "Versuch $retryCount/$($MaxRetries): Starte Tunnel..."

    # Prüfe ob App erreichbar ist
    if (-not (Test-AppReachable)) {
        Write-Log "⚠️  App auf Port $Port nicht erreichbar! Warte und versuche trotzdem..."
    } else {
        Write-Log "✅ App ist erreichbar auf http://127.0.0.1:$Port"
    }

    # Starte cloudflared mit Timeout
    $tunnelLog = "cloudflared_attempt_$retryCount.log"
    Write-Log "Starte: .$cloudflaredPath tunnel --url http://127.0.0.1:$Port > $tunnelLog 2>&1"

    $job = Start-Job -ScriptBlock {
        param($exe, $port, $log)
        & $exe tunnel --url "http://127.0.0.1:$port" > $log 2>&1
    } -ArgumentList $cloudflaredPath, $Port, $tunnelLog

    # Warte auf Tunnel-URL (max 15 Sekunden)
    Write-Log "Warte auf Tunnel-Registration (max 15s)..."
    $waitTime = 0
    $maxWait = 15

    while ($waitTime -lt $maxWait -and -not $tunnelUrl) {
        Start-Sleep -Seconds 1
        $waitTime++

        if (Test-Path $tunnelLog) {
            $content = Get-Content $tunnelLog -Raw -ErrorAction SilentlyContinue
            $tunnelUrl = Extract-TunnelUrl $content

            if ($tunnelUrl) {
                Write-Log "✅ TUNNEL-URL GEFUNDEN: $tunnelUrl"
                break
            }
        }
    }

    if ($tunnelUrl) {
        # Tunnel erfolgreich erstellt
        Write-Log "🎉 Tunnel erfolgreich registriert!"
        Write-Log "URL: $tunnelUrl"

        # Speichere URL in separater Datei für einfachen Zugriff
        $tunnelUrl | Out-File -FilePath $tunnelUrlFile -Force
        Write-Log "URL gespeichert in: $tunnelUrlFile"

        # Halte den Job im Vordergrund
        Wait-Job -Job $job
        break
    } else {
        # Kein Erfolg, stoppe Job und versuche erneut
        Write-Log "❌ Tunnel-URL nicht erhalten in Versuch $retryCount. Beende Job..."
        Stop-Job -Job $job -Force
        Remove-Job -Job $job
        taskkill /IM cloudflared.exe /F 2>&1 | Out-Null

        if ($retryCount -lt $MaxRetries) {
            Write-Log "Warte $($RetryDelaySeconds)s vor Versuch $($retryCount + 1)..."
            Start-Sleep -Seconds $RetryDelaySeconds
        }
    }
}

if ($tunnelUrl) {
    Write-Log "=========================================="
    Write-Log "TUNNEL AKTIV"
    Write-Log "URL: $tunnelUrl"
    Write-Log "=========================================="
    Write-Log "Tunnel läuft im Hintergrund. Beende dieses Fenster NICHT!"

    # Halte den Prozess laufen
    while ($true) {
        $proc = Get-Process cloudflared -ErrorAction SilentlyContinue
        if (-not $proc) {
            Write-Log "⚠️  Tunnel-Prozess beendet! Versuche neu zu starten..."
            Start-Sleep -Seconds 5
        } else {
            Start-Sleep -Seconds 10
        }
    }
} else {
    Write-Log "❌ FEHLER: Konnte Tunnel nach $MaxRetries Versuchen nicht starten!"
    exit 1
}



