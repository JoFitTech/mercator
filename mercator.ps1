param(
    [ValidateSet("start", "stop", "restart", "status", "logs", "init-db", "open", "cleanup")]
    [string]$Action = "status",
    [string]$Service = "app"
)

$ErrorActionPreference = "Stop"
$composeFile = Join-Path $PSScriptRoot "mercator-compose.yml"

Set-Location -Path $PSScriptRoot

# Hilfsfunktion zum Bereinigen von verwaisten Containern
function Remove-Legacy-Containers {
    Write-Host "Suche nach alten Mercator-Containern..." -ForegroundColor Cyan
    $legacyContainers = docker ps -a --filter "name=mercator-" --format "{{.Names}}"
    if ($legacyContainers) {
        Write-Host "Gefundene alte Container: $legacyContainers" -ForegroundColor Yellow
        docker stop $legacyContainers 2>$null
        docker rm $legacyContainers 2>$null
        Write-Host "Alte Container entfernt." -ForegroundColor Green
    } else {
        Write-Host "Keine alten Mercator-Container gefunden." -ForegroundColor Gray
    }
}

function Invoke-Compose {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Args
    )

    $oldEAP = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        docker compose -f $composeFile @Args
    } finally {
        $ErrorActionPreference = $oldEAP
    }

    if ($LASTEXITCODE -ne 0) {
        $joinedArgs = $Args -join " "
        throw "docker compose -f $composeFile $joinedArgs fehlgeschlagen (ExitCode $LASTEXITCODE)."
    }
}

function Invoke-ComposeQuiet {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$ComposeArgs
    )

    $joinedArgs = $ComposeArgs -join " "
    # Fuehre den Befehl aus und fange stderr ab, um es im Fehlerfall anzuzeigen.
    $errorFile = Join-Path $env:TEMP "mercator_compose_error.tmp"
    
    $oldEAP = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        docker compose -f $composeFile @ComposeArgs 2>$errorFile >$null
    } finally {
        $ErrorActionPreference = $oldEAP
    }

    if ($LASTEXITCODE -ne 0) {
        $errorMessage = Get-Content $errorFile -Raw
        Remove-Item $errorFile -ErrorAction SilentlyContinue
        Write-Host "`nFehler beim Ausfuehren von: docker compose -f $composeFile $joinedArgs" -ForegroundColor Red
        if ($errorMessage) {
            Write-Host "Fehlermeldung:`n$errorMessage" -ForegroundColor Yellow
        }
        throw "docker compose -f $composeFile $joinedArgs fehlgeschlagen (ExitCode $LASTEXITCODE)."
    }
    Remove-Item $errorFile -ErrorAction SilentlyContinue
}

switch ($Action) {
    "start" {
        # Startet den Stack still im Hintergrund; Details erscheinen nur im Fehlerfall.
        Invoke-ComposeQuiet up -d --wait
        Write-Host "FinanzPort Academic gestartet. App: http://localhost:8501" -ForegroundColor Green
    }
    "stop" {
        Invoke-Compose down
        Write-Host "FinanzPort Academic gestoppt." -ForegroundColor Yellow
    }
    "restart" {
        Invoke-ComposeQuiet down
        Remove-Legacy-Containers
        Invoke-ComposeQuiet up -d --wait
        Write-Host "FinanzPort Academic neu gestartet. App: http://localhost:8501" -ForegroundColor Green
    }
    "status" {
        Invoke-Compose ps
    }
    "logs" {
        Invoke-Compose logs -f $Service
    }
    "init-db" {
        # Stellt sicher, dass App und lokale Datenbanken laufen, bevor das Schema initialisiert wird.
        Invoke-ComposeQuiet up -d --wait app mysql mongo
        # Fuehrt den MySQL-Schema-Init innerhalb des App-Containers aus.
        Invoke-Compose exec app python -m src.scripts.init_mysql_schema
    }
    "open" {
        Start-Process "http://localhost:8501"
    }
    "cleanup" {
        # Entfernt alte Container, die nicht zum neuen Stack gehoeren (Name 'mercator-*').
        Remove-Legacy-Containers
        # Optional: Raeumt auch den aktuellen Stack auf.
        Invoke-Compose down --remove-orphans
        Write-Host "Cleanup abgeschlossen." -ForegroundColor Green
    }
}
