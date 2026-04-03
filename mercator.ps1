param(
    [ValidateSet("start", "stop", "restart", "status", "logs", "init-db", "open")]
    [string]$Action = "status",
    [string]$Service = "app"
)

$ErrorActionPreference = "Stop"
$composeFile = Join-Path $PSScriptRoot "mercator-compose.yml"

Set-Location -Path $PSScriptRoot

function Invoke-Compose {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Args
    )

    docker compose -f $composeFile @Args

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
    $command = "docker compose -f `"$composeFile`" $joinedArgs >nul 2>nul"
    cmd.exe /d /c $command | Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "docker compose -f $composeFile $joinedArgs fehlgeschlagen (ExitCode $LASTEXITCODE)."
    }
}

switch ($Action) {
    "start" {
        # Startet den Stack still im Hintergrund; Details erscheinen nur im Fehlerfall.
        Invoke-ComposeQuiet up -d --wait
        Write-Host "Mercator gestartet. App: http://localhost:8501" -ForegroundColor Green
    }
    "stop" {
        Invoke-Compose down
        Write-Host "Mercator gestoppt." -ForegroundColor Yellow
    }
    "restart" {
        Invoke-ComposeQuiet down
        Invoke-ComposeQuiet up -d --wait
        Write-Host "Mercator neu gestartet. App: http://localhost:8501" -ForegroundColor Green
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
}
