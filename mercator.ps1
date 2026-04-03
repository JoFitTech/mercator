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

switch ($Action) {
    "start" {
        Invoke-Compose up -d
        Write-Host "Mercator gestartet. App: http://localhost:8501" -ForegroundColor Green
    }
    "stop" {
        Invoke-Compose down
        Write-Host "Mercator gestoppt." -ForegroundColor Yellow
    }
    "restart" {
        Invoke-Compose down
        Invoke-Compose up -d
        Write-Host "Mercator neu gestartet. App: http://localhost:8501" -ForegroundColor Green
    }
    "status" {
        Invoke-Compose ps
    }
    "logs" {
        Invoke-Compose logs -f $Service
    }
    "init-db" {
        # Fuehrt den MySQL-Schema-Init innerhalb des App-Containers aus.
        Invoke-Compose exec app python -m src.scripts.init_mysql_schema
    }
    "open" {
        Start-Process "http://localhost:8501"
    }
}

