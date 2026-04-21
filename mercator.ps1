param(
    [ValidateSet("start", "stop", "restart", "status", "logs", "init-db", "open", "cleanup", "doctor", "e2e-install", "e2e-smoke", "e2e", "share-start", "share-stop", "share-status", "share-logs")]
    [string]$Action = "status",
    [string]$Service = "app"
)

$ErrorActionPreference = "Stop"
$composeFile = Join-Path $PSScriptRoot "mercator-compose.yml"

Set-Location -Path $PSScriptRoot

function Get-DockerAvailability {
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCmd) {
        return @{
            IsAvailable = $false
            Message = "Docker CLI wurde nicht gefunden. Bitte Docker Desktop installieren oder starten."
        }
    }

    $outFile = Join-Path $env:TEMP "mercator_docker_check_out.tmp"
    $errorFile = Join-Path $env:TEMP "mercator_docker_check_error.tmp"
    Remove-Item $outFile -ErrorAction SilentlyContinue
    Remove-Item $errorFile -ErrorAction SilentlyContinue

    $proc = Start-Process -FilePath $dockerCmd.Source `
        -ArgumentList @('version', '--format', '{{.Server.Version}}') `
        -RedirectStandardOutput $outFile `
        -RedirectStandardError $errorFile `
        -PassThru `
        -Wait `
        -WindowStyle Hidden
    $exitCode = $proc.ExitCode

    if ($exitCode -eq 0) {
        Remove-Item $outFile, $errorFile -ErrorAction SilentlyContinue
        return @{
            IsAvailable = $true
            Message = "Docker daemon verfuegbar."
        }
    }

    $detail = Get-Content $errorFile -Raw -ErrorAction SilentlyContinue
    if (-not $detail) {
        $detail = Get-Content $outFile -Raw -ErrorAction SilentlyContinue
    }
    if (-not $detail) {
        $detail = "Docker daemon ist aktuell nicht erreichbar."
    }

    Remove-Item $outFile, $errorFile -ErrorAction SilentlyContinue

    return @{
        IsAvailable = $false
        Message = $detail
    }
}

function Ensure-DockerAvailable {
    param(
        [Parameter(Mandatory=$true)][string]$Context,
        [switch]$AllowMissing
    )

    $dockerState = Get-DockerAvailability
    if ($dockerState.IsAvailable) {
        return $true
    }

    $message = "Docker ist nicht verfuegbar. $Context`nDetails: $($dockerState.Message)"
    if ($AllowMissing) {
        Write-Host $message -ForegroundColor Yellow
        return $false
    }

    throw $message
}

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

function Get-ConfigValue {
    param(
        [Parameter(Mandatory=$true)][string]$Key,
        [string]$Default = ""
    )
    $envValue = [Environment]::GetEnvironmentVariable($Key)
    if ($envValue -and $envValue.Trim()) { return $envValue.Trim() }
    $dotEnvValue = Get-DotEnvValue -Key $Key
    if ($dotEnvValue -and $dotEnvValue.Trim()) { return $dotEnvValue.Trim() }
    return $Default
}

function Resolve-RepoPath {
    param([Parameter(Mandatory=$true)][string]$RawPath)
    if (-not $RawPath) { return $null }
    if ([System.IO.Path]::IsPathRooted($RawPath)) { return $RawPath }
    return Join-Path $PSScriptRoot $RawPath
}

function Ensure-PublicSharePaths {
    $statusPath = Resolve-RepoPath (Get-ConfigValue "PUBLIC_SHARE_STATUS_FILE" ".mercator/public-share/status.json")
    $logPath = Resolve-RepoPath (Get-ConfigValue "PUBLIC_SHARE_LOG_FILE" ".mercator/public-share/cloudflared.log")
    $errorLogPath = Resolve-RepoPath (Get-ConfigValue "PUBLIC_SHARE_ERROR_LOG_FILE" ".mercator/public-share/cloudflared-error.log")
    $pidPath = Resolve-RepoPath (Get-ConfigValue "PUBLIC_SHARE_PID_FILE" ".mercator/public-share/pid.txt")
    $dir = Split-Path -Parent $statusPath
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $logDir = Split-Path -Parent $logPath
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
    $errorLogDir = Split-Path -Parent $errorLogPath
    if (-not (Test-Path $errorLogDir)) { New-Item -ItemType Directory -Path $errorLogDir -Force | Out-Null }
    return @{ StatusPath = $statusPath; LogPath = $logPath; ErrorLogPath = $errorLogPath; PidPath = $pidPath }
}

function Write-PublicShareStatus {
    param(
        [Parameter(Mandatory=$true)][hashtable]$Paths,
        [Parameter(Mandatory=$true)][hashtable]$Status
    )
    $json = $Status | ConvertTo-Json -Depth 6
    Set-Content -Path $Paths.StatusPath -Value $json -Encoding UTF8
}

function Get-PublicSharePid {
    param([Parameter(Mandatory=$true)][string]$PidPath)
    if (-not (Test-Path $PidPath)) { return $null }
    try {
        $raw = (Get-Content -Path $PidPath -Raw).Trim()
        if (-not $raw) { return $null }
        return [int]$raw
    } catch {
        return $null
    }
}

function Get-CloudflaredBinaryPath {
    $configured = Get-ConfigValue "CLOUDFLARED_BIN" "cloudflared"
    $candidate = Get-Command $configured -ErrorAction SilentlyContinue
    if ($candidate) { return $candidate.Source }
    $exeCandidate = Join-Path $PSScriptRoot "cloudflared.exe"
    if (Test-Path $exeCandidate) { return $exeCandidate }
    throw "cloudflared wurde nicht gefunden. Bitte cloudflared installieren oder CLOUDFLARED_BIN setzen."
}

function Get-CloudflaredExtraArgs {
    $raw = Get-ConfigValue "PUBLIC_SHARE_CLOUDFLARED_EXTRA_ARGS" ""
    if (-not $raw) { return @() }
    return @($raw -split "\s+" | Where-Object { $_ -and $_.Trim() })
}

function Get-CloudflaredPublicUrl {
    param([Parameter(Mandatory=$true)][hashtable]$Paths)

    $chunks = @()
    foreach ($path in @($Paths.LogPath, $Paths.ErrorLogPath)) {
        if (Test-Path $path) {
            $raw = Get-Content -Path $path -Raw -ErrorAction SilentlyContinue
            if ($raw) { $chunks += $raw }
        }
    }
    if (-not $chunks -or $chunks.Count -eq 0) { return $null }

    $combined = ($chunks -join "`n")
    $matches = [regex]::Matches($combined, "https://[a-zA-Z0-9.-]+\.trycloudflare\.com")
    if ($matches.Count -gt 0) {
        return $matches[$matches.Count - 1].Value
    }
    return $null
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
    # Fuer den Uni-Check niemals auf MONGO_URI zurueckfallen, sonst entstehen False-Positives auf localhost.
    $mongoUri = Get-DotEnvValue "UNI_MONGO_URI"
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
     if (-not (Ensure-DockerAvailable -Context "Legacy-Container koennen ohne Docker nicht bereinigt werden." -AllowMissing)) {
         return
     }
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
        if ((Ensure-DockerAvailable -Context "Docker-Port-Mapping kann nicht gelesen werden." -AllowMissing)) {
            $ports = docker ps --filter "name=^/mercator-app$" --format "{{.Ports}}"
            if ($ports) {
                # Beispiel: 127.0.0.1:8501->8501/tcp
                $m = [regex]::Match(($ports | Out-String), "127\.0\.0\.1:(\d+)->")
                if ($m.Success) {
                    return "http://localhost:$($m.Groups[1].Value)"
                }
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

    Ensure-DockerAvailable -Context "Der Docker-Compose-Befehl kann nicht ausgefuehrt werden."

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

    Ensure-DockerAvailable -Context "Der Docker-Compose-Befehl kann nicht ausgefuehrt werden."

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

function Invoke-ShareStart {
    $paths = Ensure-PublicSharePaths
    $executionMode = (Get-ConfigValue "PUBLIC_SHARE_EXECUTION_MODE" "host").ToLowerInvariant()
    if ($executionMode -ne "host") {
        throw "share-start ist nur für PUBLIC_SHARE_EXECUTION_MODE=host verfügbar (aktuell: $executionMode)."
    }
    $localUrl = Get-ConfigValue "PUBLIC_SHARE_LOCAL_URL" (Get-AppUrl)
    try {
        $health = Invoke-WebRequest -Uri $localUrl -Method Get -TimeoutSec 4 -UseBasicParsing
        if (-not $health.StatusCode) { throw "Lokale App antwortet nicht." }
    } catch {
        throw "Lokale App unter $localUrl nicht erreichbar. Bitte zuerst .\mercator.ps1 start ausführen."
    }

    $existingPid = Get-PublicSharePid -PidPath $paths.PidPath
    if ($existingPid) {
        $existingProcess = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
        if ($existingProcess) {
            Write-Host "Host-Tunnel läuft bereits mit PID $existingPid. Wiederverwendung." -ForegroundColor Yellow
            Invoke-ShareStatus
            return
        }
        Remove-Item $paths.PidPath -ErrorAction SilentlyContinue
    }

    $bin = Get-CloudflaredBinaryPath
    $extraArgs = Get-CloudflaredExtraArgs
    $arguments = @("tunnel", "--url", $localUrl) + $extraArgs
    Set-Content -Path $paths.LogPath -Value "" -Encoding UTF8
    Set-Content -Path $paths.ErrorLogPath -Value "" -Encoding UTF8

    $proc = Start-Process -FilePath $bin -ArgumentList $arguments -RedirectStandardOutput $paths.LogPath -RedirectStandardError $paths.ErrorLogPath -PassThru -WindowStyle Hidden
    Start-Sleep -Milliseconds 900
    $publicUrl = $null
    for ($i = 0; $i -lt 10 -and -not $publicUrl; $i++) {
        $publicUrl = Get-CloudflaredPublicUrl -Paths $paths
        if (-not $publicUrl) { Start-Sleep -Milliseconds 400 }
    }

    $status = if ($proc.HasExited) { "ERROR" } elseif ($publicUrl) { "RUNNING" } else { "STARTING" }
    $lastExitCode = if ($proc.HasExited) { $proc.ExitCode } else { $null }
    $lastError = if ($proc.HasExited) { "cloudflared wurde beendet." } else { $null }
    $statusPayload = @{
        execution_mode = "host"
        provider = (Get-ConfigValue "PUBLIC_SHARE_PROVIDER" "cloudflare")
        local_url = $localUrl
        public_url = $publicUrl
        pid = $proc.Id
        started_at = (Get-Date).ToUniversalTime().ToString("o")
        status = $status
        last_error = $lastError
        last_exit_code = $lastExitCode
        extra_args = $extraArgs
    }
    Write-PublicShareStatus -Paths $paths -Status $statusPayload
    Set-Content -Path $paths.PidPath -Value "$($proc.Id)" -Encoding UTF8
    Write-Host "Host-Tunnel gestartet (PID $($proc.Id))." -ForegroundColor Green
    if ($publicUrl) { Write-Host "Public URL: $publicUrl" -ForegroundColor Green }
}

function Invoke-ShareStop {
    $paths = Ensure-PublicSharePaths
    $sharePid = Get-PublicSharePid -PidPath $paths.PidPath
    $lastExitCode = $null
    if ($sharePid) {
        $process = Get-Process -Id $sharePid -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $sharePid -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 350
            $alive = Get-Process -Id $sharePid -ErrorAction SilentlyContinue
            if ($alive) { Stop-Process -Id $sharePid -Force -ErrorAction SilentlyContinue }
        }
    }
    Remove-Item $paths.PidPath -ErrorAction SilentlyContinue
    $payload = @{
        execution_mode = "host"
        provider = (Get-ConfigValue "PUBLIC_SHARE_PROVIDER" "cloudflare")
        local_url = Get-ConfigValue "PUBLIC_SHARE_LOCAL_URL" "http://localhost:8501"
        public_url = $null
        pid = $null
        started_at = (Get-Date).ToUniversalTime().ToString("o")
        status = "STOPPED"
        last_error = $null
        last_exit_code = $lastExitCode
        extra_args = Get-CloudflaredExtraArgs
    }
    Write-PublicShareStatus -Paths $paths -Status $payload
    Write-Host "Host-Tunnel gestoppt." -ForegroundColor Yellow
}

function Invoke-ShareStatus {
    $paths = Ensure-PublicSharePaths
    if (-not (Test-Path $paths.StatusPath)) {
        Write-Host "Kein Public-Share-Status gefunden." -ForegroundColor Yellow
        return
    }
    $status = Get-Content -Path $paths.StatusPath -Raw | ConvertFrom-Json
    $sharePid = Get-PublicSharePid -PidPath $paths.PidPath
    $alive = $false
    if ($sharePid) { $alive = [bool](Get-Process -Id $sharePid -ErrorAction SilentlyContinue) }
    if ($alive -and (-not $status.public_url -or -not "$($status.public_url)".Trim())) {
        $detectedUrl = Get-CloudflaredPublicUrl -Paths $paths
        if ($detectedUrl) {
            $status.public_url = $detectedUrl
            if ($status.status -eq "STARTING") { $status.status = "RUNNING" }
            Write-PublicShareStatus -Paths $paths -Status @{
                execution_mode = $status.execution_mode
                provider = $status.provider
                local_url = $status.local_url
                public_url = $status.public_url
                pid = $sharePid
                started_at = $status.started_at
                status = $status.status
                last_error = $status.last_error
                last_exit_code = $status.last_exit_code
                extra_args = $status.extra_args
            }
        }
    }
    if ($sharePid -and -not $alive) {
        $status.status = "STALE"
        $status.last_error = "PID-Datei verweist auf keinen laufenden Prozess."
        $status.pid = $null
        Remove-Item $paths.PidPath -ErrorAction SilentlyContinue
        Write-PublicShareStatus -Paths $paths -Status @{
            execution_mode = $status.execution_mode
            provider = $status.provider
            local_url = $status.local_url
            public_url = $status.public_url
            pid = $null
            started_at = $status.started_at
            status = "STALE"
            last_error = $status.last_error
            last_exit_code = $status.last_exit_code
            extra_args = $status.extra_args
        }
    }
    Write-Host "Execution Mode: $($status.execution_mode)"
    Write-Host "Status: $($status.status)"
    Write-Host "Local URL: $($status.local_url)"
    Write-Host "Public URL: $(if($status.public_url){$status.public_url}else{'-'})"
    Write-Host "PID: $(if($sharePid){$sharePid}else{'-'})"
    if ($status.last_error) { Write-Host "Fehler: $($status.last_error)" -ForegroundColor Red }
}

function Invoke-ShareLogs {
    $paths = Ensure-PublicSharePaths
    if (-not (Test-Path $paths.LogPath)) {
        Write-Host "Noch keine Logdatei vorhanden: $($paths.LogPath)" -ForegroundColor Yellow
        return
    }
    Get-Content -Path $paths.LogPath -Tail 80
}

switch ($Action) {
    "start" {
        # Pruefe zuerst die Uni-DBs. Wenn beide erreichbar sind, starte nur die App ohne lokale DB-Services.
        # WICHTIG: --build wird standardmaessig hinzugefuegt um sicherzustellen, dass Dockerfile-Aenderungen (z.B. cloudflared) geladen werden.
        $uni = Test-UniDatabaseConnectivity
        if ($uni.MySql -and $uni.Mongo) {
            Write-Host "Uni-Datenbanken erreichbar. Starte nur die App (ohne lokale DB-Services)..." -ForegroundColor Cyan
            Invoke-ComposeQuiet up -d --build --wait --no-deps app
        } else {
            Write-Host "Uni-Datenbanken nicht vollständig erreichbar. Starte kompletten lokalen Stack..." -ForegroundColor Yellow
            Invoke-ComposeQuiet up -d --build --wait
        }
        $appUrl = Get-AppUrl
        Write-Host "Mercator gestartet. App: $appUrl" -ForegroundColor Green
    }
    "stop" {
        if (-not (Ensure-DockerAvailable -Context "Es gibt keinen Docker-Stack zum Stoppen." -AllowMissing)) {
            Write-Host "Mercator-Stop uebersprungen: Docker Desktop/Daemon laeuft nicht." -ForegroundColor Yellow
            break
        }
        Invoke-Compose down
        Write-Host "Mercator gestoppt." -ForegroundColor Yellow
    }
    "restart" {
        Invoke-ComposeQuiet down
        Remove-Legacy-Containers
        # Pruefe zuerst die Uni-DBs. Wenn beide erreichbar sind, starte nur die App ohne lokale DB-Services.
        # WICHTIG: --build wird standardmaessig hinzugefuegt um sicherzustellen, dass Dockerfile-Aenderungen geladen werden.
        $uni = Test-UniDatabaseConnectivity
        if ($uni.MySql -and $uni.Mongo) {
            Write-Host "Uni-Datenbanken erreichbar. Starte nur die App (ohne lokale DB-Services)..." -ForegroundColor Cyan
            Invoke-ComposeQuiet up -d --build --wait --no-deps app
        } else {
            Write-Host "Uni-Datenbanken nicht vollständig erreichbar. Starte kompletten lokalen Stack..." -ForegroundColor Yellow
            Invoke-ComposeQuiet up -d --build --wait
        }
        $appUrl = Get-AppUrl
        Write-Host "Mercator neu gestartet. App: $appUrl" -ForegroundColor Green
    }
    "status" {
        if (-not (Ensure-DockerAvailable -Context "Docker-Status kann nicht abgefragt werden." -AllowMissing)) {
            Write-Host "Mercator-Status: Docker nicht verfuegbar. Lokale DB-Container laufen daher nicht." -ForegroundColor Yellow
            break
        }
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
        if (-not (Ensure-DockerAvailable -Context "Cleanup des Docker-Stacks kann nicht ausgefuehrt werden." -AllowMissing)) {
            Write-Host "Cleanup uebersprungen: Docker Desktop/Daemon laeuft nicht." -ForegroundColor Yellow
            break
        }
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
    "share-start" {
        Invoke-ShareStart
    }
    "share-stop" {
        Invoke-ShareStop
    }
    "share-status" {
        Invoke-ShareStatus
    }
    "share-logs" {
        Invoke-ShareLogs
    }
}
