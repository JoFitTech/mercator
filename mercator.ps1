param(
    [ValidateSet("start", "stop", "restart", "status", "logs", "init-db", "open", "cleanup", "doctor", "e2e-install", "e2e-smoke", "e2e")]
    [string]$Action = "status",
    [string]$Service = "app"
)

$ErrorActionPreference = "Stop"
$composeFile = Join-Path $PSScriptRoot "mercator-compose.yml"

Set-Location -Path $PSScriptRoot

# Hilfsfunktionen zum Lesen von .env und Prüfen der Uni-DB-Erreichbarkeit
function Get-DotEnvValue {
    param([Parameter(Mandatory=$true)][string]$Key)
    $envPath = Join-Path $PSScriptRoot ".env"
    if (-not (Test-Path $envPath)) { return $null }
    $line = Select-String -Path $envPath -Pattern "^\s*$Key\s*=" | Select-Object -First 1
    if (-not $line) { return $null }
    $value = ($line.Line -split "=",2)[1].Trim()
    if ($value.StartsWith('"') -and $value.EndsWith('"')) { $value = $value.Trim('"') }
    if ($value.StartsWith("'") -and $value.EndsWith("'")) { $value = $value.Trim("'") }
    return $value
}

function Get-MongoHostPortFromUri {
    param([string]$Uri)
    if (-not $Uri) { return @{ Host = $null; Port = $null } }
    $pattern = 'mongodb://(?:[^@/]+@)?([^:/]+)(?::(\d+))?'
    $m = [regex]::Match($Uri, $pattern)
    if ($m.Success) {
        $mHost = $m.Groups[1].Value
        $mPort = if ($m.Groups[2].Success) { [int]$m.Groups[2].Value } else { 27017 }
        return @{ Host = $mHost; Port = $mPort }
    }
    return @{ Host = $null; Port = $null }
}

function Test-UniDatabaseConnectivity {
    $mysqlHost = Get-DotEnvValue "UNI_MYSQL_HOST"
    $mysqlPort = (Get-DotEnvValue "UNI_MYSQL_PORT")
    if (-not $mysqlPort) { $mysqlPort = "3306" }
    $mongoUri = Get-DotEnvValue "UNI_MONGO_URI"
    if (-not $mongoUri) { $mongoUri = Get-DotEnvValue "MONGO_URI" }
    $mongo = Get-MongoHostPortFromUri -Uri $mongoUri

    $mysqlOk = $false
    $mongoOk = $false

    if ($mysqlHost) {
        try {
            $mysqlOk = Test-NetConnection -ComputerName $mysqlHost -Port ([int]$mysqlPort) -InformationLevel Quiet
        } catch { $mysqlOk = $false }
    }
    if ($mongo.Host) {
        try {
            $mongoOk = Test-NetConnection -ComputerName $mongo.Host -Port ([int]$mongo.Port) -InformationLevel Quiet
        } catch { $mongoOk = $false }
    }

    return @{ MySql = $mysqlOk; Mongo = $mongoOk }
}

# Hilfsfunktion zum Bereinigen von verwaisten Containern
function Remove-Legacy-Containers {
     Write-Host "Suche nach alten Mercator-Containern..." -ForegroundColor Cyan
     # Docker behandelt mehrere name-Filter mit AND – daher separat abfragen und zusammenführen
     $mercatorContainers = @(docker ps -a --filter "name=mercator-" --format "{{.Names}}" 2>$null) | Where-Object { $_ -match '\S' }
     $legacyContainers = @($mercatorContainers) | Select-Object -Unique | Where-Object { $_ -match '\S' }
     if ($legacyContainers -and $legacyContainers.Count -gt 0) {
         Write-Host "Gefundene alte Container: $($legacyContainers -join ', ')" -ForegroundColor Yellow
         foreach ($container in $legacyContainers) {
             docker stop $container 2>$null | Out-Null
             docker rm $container 2>$null | Out-Null
         }
         Write-Host "Alte Container entfernt." -ForegroundColor Green
     } else {
         Write-Host "Keine alten Mercator-Container gefunden." -ForegroundColor Gray
     }
 }

function Get-AppUrl {
    <#
    Ermittelt die beste lokale URL fuer die App:
    1) Docker-Port-Mapping des laufenden `mercator-app` Containers
    2) Letzte Streamlit-Logdatei (`streamlit_*.log`) und deren `Local URL`
    3) Fallback auf localhost:8501
    #>

    try {
        $ports = docker ps --filter "name=^/mercator-app$" --format "{{.Ports}}"
        if ($ports) {
            # Beispiel: 127.0.0.1:8501->8501/tcp
            $m = [regex]::Match(($ports | Out-String), "127\.0\.0\.1:(\d+)->")
            if ($m.Success) {
                return "http://localhost:$($m.Groups[1].Value)"
            }
        }
    } catch {
        # Docker nicht verfuegbar oder kein laufender Container.
    }

    try {
        $latestLog = Get-ChildItem -Path $PSScriptRoot -Filter "streamlit_*.log" -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($latestLog) {
            $line = Select-String -Path $latestLog.FullName -Pattern "^\s*Local URL:\s*(http://\S+)" | Select-Object -Last 1
            if ($line -and $line.Matches.Count -gt 0) {
                return $line.Matches[0].Groups[1].Value
            }
        }
    } catch {
        # Keine Logdatei verfuegbar oder nicht parsebar.
    }

    return "http://localhost:8501"
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

function Get-PythonCommand {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) { return $pythonCmd.Source }

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) { return "$($pyLauncher.Source) -3" }

    throw "Python wurde nicht gefunden. Installiere Python 3.11+ oder aktiviere eine virtuelle Umgebung."
}

function Invoke-PythonModule {
    param(
        [Parameter(Mandatory=$true)][string]$Module,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$ModuleArgs
    )

    $pythonCommand = Get-PythonCommand
    if ($pythonCommand -like "* -3") {
        $parts = $pythonCommand -split " "
        & $parts[0] $parts[1] -m $Module @ModuleArgs
    } else {
        & $pythonCommand -m $Module @ModuleArgs
    }

    if ($LASTEXITCODE -ne 0) {
        throw "python -m $Module $($ModuleArgs -join ' ') fehlgeschlagen (ExitCode $LASTEXITCODE)."
    }
}

switch ($Action) {
    "start" {
        # Pruefe zuerst die Uni-DBs. Wenn beide erreichbar sind, starte nur die App ohne lokale DB-Services.
        $uni = Test-UniDatabaseConnectivity
        if ($uni.MySql -and $uni.Mongo) {
            Write-Host "Uni-Datenbanken erreichbar. Starte nur die App (ohne lokale DB-Services)..." -ForegroundColor Cyan
            Invoke-ComposeQuiet up -d --wait --no-deps app
        } else {
            Write-Host "Uni-Datenbanken nicht vollständig erreichbar. Starte kompletten lokalen Stack..." -ForegroundColor Yellow
            Invoke-ComposeQuiet up -d --wait
        }
        $appUrl = Get-AppUrl
        Write-Host "Mercator gestartet. App: $appUrl" -ForegroundColor Green
    }
    "stop" {
        Invoke-Compose down
        Write-Host "Mercator gestoppt." -ForegroundColor Yellow
    }
    "restart" {
        Invoke-ComposeQuiet down
        Remove-Legacy-Containers
        # Pruefe zuerst die Uni-DBs. Wenn beide erreichbar sind, starte nur die App ohne lokale DB-Services.
        $uni = Test-UniDatabaseConnectivity
        if ($uni.MySql -and $uni.Mongo) {
            Write-Host "Uni-Datenbanken erreichbar. Starte nur die App (ohne lokale DB-Services)..." -ForegroundColor Cyan
            Invoke-ComposeQuiet up -d --wait --no-deps app
        } else {
            Write-Host "Uni-Datenbanken nicht vollständig erreichbar. Starte kompletten lokalen Stack..." -ForegroundColor Yellow
            Invoke-ComposeQuiet up -d --wait
        }
        $appUrl = Get-AppUrl
        Write-Host "Mercator neu gestartet. App: $appUrl" -ForegroundColor Green
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
        # Fuehrt die MySQL-Schema-Init fuer ALLE Ziele innerhalb des App-Containers aus.
        Invoke-Compose exec app python -m src.scripts.init_mysql_schema
    }
    "doctor" {
        # Stellt sicher, dass App läuft
        Invoke-ComposeQuiet up -d --wait app
        # Startet den DB-Doctor im App-Container
        Invoke-Compose exec app python -m src.scripts.db_doctor
    }
    "open" {
        $appUrl = Get-AppUrl
        Start-Process $appUrl
    }
    "cleanup" {
        # Entfernt alte Container, die nicht zum neuen Stack gehoeren (Name 'mercator-*').
        Remove-Legacy-Containers
        # Optional: Raeumt auch den aktuellen Stack auf.
        Invoke-Compose down --remove-orphans
        Write-Host "Cleanup abgeschlossen." -ForegroundColor Green
    }
    "e2e-install" {
        Write-Host "Installiere Dev- und E2E-Abhaengigkeiten..." -ForegroundColor Cyan
        Invoke-PythonModule pip install -r requirements-dev.txt
        Write-Host "Installiere Playwright Chromium..." -ForegroundColor Cyan
        Invoke-PythonModule playwright install chromium
        Write-Host "E2E-Setup abgeschlossen." -ForegroundColor Green
    }
    "e2e-smoke" {
        $appUrl = Get-AppUrl
        $env:MERCATOR_E2E_BASE_URL = $appUrl
        Write-Host "Starte Smoke-E2E gegen $appUrl" -ForegroundColor Cyan
        Invoke-PythonModule pytest tests/e2e/ -m smoke -v
    }
    "e2e" {
        $appUrl = Get-AppUrl
        $env:MERCATOR_E2E_BASE_URL = $appUrl
        Write-Host "Starte komplette E2E-Suite gegen $appUrl" -ForegroundColor Cyan
        Invoke-PythonModule pytest tests/e2e/ -v
    }
}
