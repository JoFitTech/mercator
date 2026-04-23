param(
    [ValidateSet("start", "stop", "restart", "share-start", "share-stop", "share-status", "share-logs", "share-reset")]
    [string]$Action = "start",
    [string]$Service = "app"
)

$ErrorActionPreference = "Stop"
$composeFile = Join-Path $PSScriptRoot "mercator-compose.yml"
$script:DockerAvailabilityCache = $null

Set-Location -Path $PSScriptRoot

function Get-DockerAvailability {
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCmd) {
        return @{
            IsAvailable = $false
            Message = "Docker CLI wurde nicht gefunden. Bitte Docker Desktop installieren oder starten."
        }
    }

    $outFile = [System.IO.Path]::GetTempFileName()
    $errorFile = [System.IO.Path]::GetTempFileName()

    $proc = Start-Process -FilePath $dockerCmd.Source `
        -ArgumentList @('version', '--format', '{{.Server.Version}}') `
        -RedirectStandardOutput $outFile `
        -RedirectStandardError $errorFile `
        -PassThru `
        -WindowStyle Hidden

    # Harte Obergrenze, damit der Start nie "haengen" bleibt.
    $finished = $proc.WaitForExit(8000)
    if (-not $finished) {
        try { $proc.Kill() } catch { }
        Remove-Item $outFile, $errorFile -ErrorAction SilentlyContinue
        return @{
            IsAvailable = $false
            Message = "Docker-Check Timeout nach 8s (docker version)."
        }
    }
    $serverVersion = (Get-Content $outFile -Raw -ErrorAction SilentlyContinue)
    if ($serverVersion -and $serverVersion.Trim()) {
        Remove-Item $outFile, $errorFile -ErrorAction SilentlyContinue
        return @{
            IsAvailable = $true
            Message = "Docker daemon verfuegbar (Server $($serverVersion.Trim()))."
        }
    }

    $detail = Get-Content $errorFile -Raw -ErrorAction SilentlyContinue
    if (-not $detail) {
        $detail = $serverVersion
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

    if ($script:DockerAvailabilityCache -and $script:DockerAvailabilityCache.IsAvailable) {
        return $true
    }

    $dockerState = Get-DockerAvailability
    $script:DockerAvailabilityCache = $dockerState
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

function Test-PublicShareUrl {
    param([string]$Url)

    if (-not $Url -or -not $Url.Trim()) {
        return @{ Ok = $false; Message = "Keine Public-URL vorhanden."; IsHardFailure = $false }
    }

    foreach ($method in @("Head", "Get")) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -Method $method -UseBasicParsing -TimeoutSec 6
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                return @{ Ok = $true; Message = $null; IsHardFailure = $false }
            }
            return @{ Ok = $false; Message = "Public URL antwortet mit HTTP $($resp.StatusCode)."; IsHardFailure = ($resp.StatusCode -ge 500) }
        } catch {
            $msg = $_.Exception.Message
            $isHard = $false

            $response = $null
            $statusCode = $null
            $body = $null
            try { $response = $_.Exception.Response } catch { $response = $null }
            if ($response) {
                try { $statusCode = [int]$response.StatusCode } catch { $statusCode = $null }
                try {
                    $stream = $response.GetResponseStream()
                    if ($stream) {
                        $reader = New-Object System.IO.StreamReader($stream)
                        $body = $reader.ReadToEnd()
                        $reader.Dispose()
                        $stream.Dispose()
                    }
                } catch {
                    $body = $null
                }
            }

            if ($statusCode -eq 530 -and $body -and ($body -match "\b1033\b" -or $body -match "Cloudflare Tunnel error")) {
                return @{
                    Ok = $false
                    Message = "Oeffentliche URL ist nicht mehr aufloesbar (Cloudflare Error 1033)."
                    IsHardFailure = $true
                }
            }

            if ($msg -match "\b1033\b" -or $msg -match "\b530\b" -or $msg -match "Cloudflare Tunnel error") {
                $isHard = $true
            }
            if ($method -eq "Get") {
                return @{ Ok = $false; Message = "Public-URL-Check fehlgeschlagen: $msg"; IsHardFailure = $isHard }
            }
        }
    }

    return @{ Ok = $false; Message = "Public-URL-Check fehlgeschlagen."; IsHardFailure = $false }
}

function Test-CloudflaredEdgeTimeouts {
    param([Parameter(Mandatory=$true)][string]$ErrorLogPath)

    if (-not (Test-Path $ErrorLogPath)) { return $false }
    $tail = Get-Content -Path $ErrorLogPath -Tail 80 -ErrorAction SilentlyContinue
    if (-not $tail) { return $false }
    $hits = @(
        $tail | Select-String -Pattern "Unable to establish connection with Cloudflare edge|Failed to dial a quic connection|dial tcp .*:7844: i/o timeout|failed to dial to edge with quic" -AllMatches
    ).Count
    return ($hits -ge 1)
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

function Wait-AppReady {
    param(
        [string]$AppUrl = "http://localhost:8501",
        [int]$TimeoutSeconds = 90,
        [int]$PollIntervalSeconds = 3,
        [switch]$BestEffort
    )

    $healthUrl = "$AppUrl/_stcore/health"
    Write-Host "      Warte auf App-Readiness: $healthUrl" -ForegroundColor Gray
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        try {
            $resp = Invoke-WebRequest -Uri $healthUrl -Method Get -UseBasicParsing -TimeoutSec 4
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {
                Write-Host "      [OK] App ist erreichbar (${elapsed}s)." -ForegroundColor Green
                return $true
            }
        } catch {
            # App noch nicht bereit
        }
        if (($elapsed % 15) -eq 0 -and $elapsed -gt 0) {
            Write-Host "      ... App startet noch ... (${elapsed}s / ${TimeoutSeconds}s)" -ForegroundColor Gray
        }
        Start-Sleep -Seconds $PollIntervalSeconds
        $elapsed += $PollIntervalSeconds
    }
    if ($BestEffort) {
        Write-Host "      [WARN] App ist nach ${TimeoutSeconds}s noch nicht bereit (Best-Effort: Start laeuft weiter)." -ForegroundColor Yellow
    } else {
        Write-Host "      [WARN] App ist nach ${TimeoutSeconds}s noch nicht bereit." -ForegroundColor Yellow
    }
    return $false
}

function Invoke-Compose {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Args
    )

    $null = Ensure-DockerAvailable -Context "Der Docker-Compose-Befehl kann nicht ausgefuehrt werden."

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

    $null = Ensure-DockerAvailable -Context "Der Docker-Compose-Befehl kann nicht ausgefuehrt werden."

    $joinedArgs = $ComposeArgs -join " "
    # Fuehre den Befehl aus und fange stderr ab, um es im Fehlerfall anzuzeigen.
    $errorFile = [System.IO.Path]::GetTempFileName()

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

    # Versuche Log-Dateien zu loeschen oder zu leeren; wenn das fehlschlaegt, ueberschreibe oder ignoriere es
    try {
        if (Test-Path $paths.LogPath) {
            Remove-Item $paths.LogPath -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path $paths.ErrorLogPath) {
            Remove-Item $paths.ErrorLogPath -Force -ErrorAction SilentlyContinue
        }
    } catch {
        # Wenn Dateien in Benutzung sind, ignoriere den Fehler
        Write-Host "Info: Log-Dateien konnten nicht geleert werden (kein Problem). Start wird fortgesetzt." -ForegroundColor Gray
    }

    $proc = Start-Process -FilePath $bin -ArgumentList $arguments -RedirectStandardOutput $paths.LogPath -RedirectStandardError $paths.ErrorLogPath -PassThru -WindowStyle Hidden
    Start-Sleep -Milliseconds 900
    $publicUrl = $null
    for ($i = 0; $i -lt 10 -and -not $publicUrl; $i++) {
        $publicUrl = Get-CloudflaredPublicUrl -Paths $paths
        if (-not $publicUrl) { Start-Sleep -Milliseconds 400 }
    }

    $status = if ($proc.HasExited) { "ERROR" } elseif ($publicUrl) { "STARTING" } else { "STARTING" }
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
    if ($publicUrl) {
        Write-Host "Public URL: $publicUrl" -ForegroundColor Green
        Write-Host "Hinweis: share-status prueft Erreichbarkeit und meldet 1033/Edge-Timeouts." -ForegroundColor Gray
    }
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

    if ($alive -and $status.public_url) {
        $publicCheck = Test-PublicShareUrl -Url "$($status.public_url)"
        $edgeTimeoutsDetected = Test-CloudflaredEdgeTimeouts -ErrorLogPath $paths.ErrorLogPath

        if ($publicCheck.Ok) {
            $status.status = "RUNNING"
            $status.last_error = $null
        } else {
            $status.status = "WARNING"
            $status.last_error = $publicCheck.Message
            if ($edgeTimeoutsDetected) {
                $status.last_error = (
                    "Tunnelprozess laeuft, aber Cloudflare-Edge-Verbindung scheitert (Timeout auf Port 7844). " +
                    "Bitte Netzwerk/FW fuer ausgehend TCP/UDP 7844 freigeben oder anderes Netz/VPN testen. " +
                    "Detail: " + $publicCheck.Message
                )
            }
        }

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

function Invoke-ShareReset {
    Invoke-ShareStop
    Start-Sleep -Milliseconds 250
    Invoke-ShareStart
}

function Wait-ContainerHealthy {
    param(
        [Parameter(Mandatory=$true)][string]$ContainerName,
        [int]$TimeoutSeconds = 90,
        [int]$PollIntervalSeconds = 2
    )
    Write-Host "  Warte auf $ContainerName (healthy)..." -ForegroundColor Gray
    $elapsed = 0
    $lastOutput = 0
    while ($elapsed -lt $TimeoutSeconds) {
        $health = docker inspect --format "{{.State.Health.Status}}" $ContainerName 2>$null
        if ($health -eq "healthy") {
            Write-Host "  [OK] $ContainerName ist healthy (${elapsed}s)." -ForegroundColor Green
            return $true
        }
        # Zeige Fortschritt alle 10 Sekunden an
        if ($elapsed - $lastOutput -ge 10) {
            Write-Host "  ... noch warten ... (${elapsed}s / ${TimeoutSeconds}s)" -ForegroundColor Gray
            $lastOutput = $elapsed
        }
        Start-Sleep -Seconds $PollIntervalSeconds
        $elapsed += $PollIntervalSeconds
    }
    Write-Host "  [WARN] $ContainerName wurde nicht healthy innerhalb von ${TimeoutSeconds}s." -ForegroundColor Yellow
    return $false
}

function Invoke-ShutdownSync {
    <#
    Fuehrt den Shutdown-Sync (local -> uni) via Python-Skript aus.
    Wird beim 'stop' aufgerufen, bevor die Container gestoppt werden.
    #>
    $uni = Test-UniDatabaseConnectivity
    if (-not $uni.MySql) {
        Write-Host "[INFO] Uni-MySQL nicht erreichbar - Shutdown-Sync wird uebersprungen." -ForegroundColor Gray
        Write-Host "       (Pending-Flag wird beim naechsten Start automatisch gesetzt)" -ForegroundColor Gray
        return
    }

    Write-Host "[SYNC] Fuehre Shutdown-Sync local -> uni durch..." -ForegroundColor Cyan
    try {
        $pythonCommand = Get-PythonCommand
        if ($pythonCommand -like "* -3") {
            $parts = $pythonCommand -split " "
            & $parts[0] $parts[1] -m src.scripts.shutdown_sync
        } else {
            & $pythonCommand -m src.scripts.shutdown_sync
        }
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Shutdown-Sync abgeschlossen." -ForegroundColor Green
        } elseif ($LASTEXITCODE -eq 1) {
            Write-Host "[WARN] Shutdown-Sync fehlgeschlagen (Daten bleiben lokal, naechster Start holt nach)." -ForegroundColor Yellow
        } else {
            Write-Host "[WARN] Shutdown-Sync konnte nicht gestartet werden (Konfigurationsfehler)." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[WARN] Shutdown-Sync-Fehler: $_" -ForegroundColor Yellow
    }
}

switch ($Action) {
    "start" {
        # Lokale DB-Services immer starten, damit Startup-Sync local -> uni stabil funktioniert.
        # WICHTIG: --build bleibt beim app-Start aktiv fuer Dockerfile-Aenderungen.
        Write-Host "`n[1/4] Pruefen Docker-Verfuegbarkeit..." -ForegroundColor Cyan
        $null = Ensure-DockerAvailable -Context "Docker wird fuer den Start benoetigt."
        Write-Host "      [OK] Docker ist verfuegbar." -ForegroundColor Green

        Write-Host "`n[2/4] Starten lokale Datenbank-Services (mysql, mongo)..." -ForegroundColor Cyan
        Invoke-Compose 'up' '-d' 'mysql' 'mongo'
        Write-Host "      [OK] Container gestartet. Warte auf Healthcheck..." -ForegroundColor Gray

        Write-Host "`n[3/4] Warten auf Datenbank-Readiness..." -ForegroundColor Cyan
        # Warte explizit bis beide Container healthy sind, bevor die App startet
        $mysqlHealthy = Wait-ContainerHealthy -ContainerName "mercator-mysql" -TimeoutSeconds 90
        $mongoHealthy = Wait-ContainerHealthy -ContainerName "mercator-mongo" -TimeoutSeconds 60
        if (-not $mysqlHealthy -or -not $mongoHealthy) {
            Write-Host "      [WARN] Nicht alle Datenbank-Container sind healthy. App wird trotzdem gestartet." -ForegroundColor Yellow
        }

        Write-Host "`n[4/4] Starten Mercator-App (mit Build-Output)..." -ForegroundColor Cyan
        Invoke-Compose 'up' '-d' '--build' 'app'
        $appUrl = Get-AppUrl
        [void](Wait-AppReady -AppUrl $appUrl -TimeoutSeconds 30 -BestEffort)

        Write-Host "`n=== ERFOLGREICH GESTARTET ===" -ForegroundColor Green
        Write-Host "App URL: $appUrl" -ForegroundColor Green
        Write-Host "(Startup-Sync local -> uni wird beim ersten Browser-Aufruf ausgefuehrt)" -ForegroundColor Gray
        Write-Host ""
    }
    "stop" {
        Invoke-ShareStop
        if (-not (Ensure-DockerAvailable -Context "Es gibt keinen Docker-Stack zum Stoppen." -AllowMissing)) {
            Write-Host "Mercator-Stop uebersprungen: Docker Desktop/Daemon laeuft nicht." -ForegroundColor Yellow
            break
        }
        # Shutdown-Sync VOR dem Stoppen der Container
        Invoke-ShutdownSync
        Invoke-Compose 'down'
        Write-Host "Mercator gestoppt." -ForegroundColor Yellow
    }
    "restart" {
        Write-Host "`n[1/5] Stoppe Cloudflare-Tunnel..." -ForegroundColor Cyan
        Invoke-ShareStop
        Write-Host "      [OK] Tunnel gestoppt." -ForegroundColor Green

        Write-Host "`n[2/5] Fuehre Shutdown-Sync local -> uni durch..." -ForegroundColor Cyan
        # Shutdown-Sync VOR dem Stoppen
        Invoke-ShutdownSync

        Write-Host "`n[3/5] Fahren Docker-Stack herunter..." -ForegroundColor Cyan
        Invoke-ComposeQuiet 'down'
        Remove-Legacy-Containers
        Write-Host "      [OK] Stack gestoppt und aufgeraeumt." -ForegroundColor Green

        Write-Host "`n[4/5] Starten lokale Datenbank-Services..." -ForegroundColor Cyan
        # Lokale DB-Services immer vor App-Start hochfahren (Startup-Sync braucht local DB-Endpunkte).
        # WICHTIG: --build bleibt beim app-Start aktiv fuer Dockerfile-Aenderungen.
        Write-Host "      [INFO] Lokale DBs werden ohne Uni-DNS-Checks gestartet." -ForegroundColor Gray
        Invoke-Compose 'up' '-d' 'mysql' 'mongo'
        Write-Host "      [OK] Container gestartet. Warte auf Healthcheck..." -ForegroundColor Gray

        $mysqlHealthy = Wait-ContainerHealthy -ContainerName "mercator-mysql" -TimeoutSeconds 90
        $mongoHealthy = Wait-ContainerHealthy -ContainerName "mercator-mongo" -TimeoutSeconds 60
        if (-not $mysqlHealthy -or -not $mongoHealthy) {
            Write-Host "      [WARN] Nicht alle Datenbank-Container sind healthy. App wird trotzdem gestartet." -ForegroundColor Yellow
        }

        Write-Host "`n[5/5] Starten Mercator-App (mit Build-Output)..." -ForegroundColor Cyan
        Invoke-Compose 'up' '-d' '--build' 'app'
        $appUrl = Get-AppUrl
        [void](Wait-AppReady -AppUrl $appUrl -TimeoutSeconds 30 -BestEffort)

        Write-Host "`n=== ERFOLGREICH NEU GESTARTET ===" -ForegroundColor Green
        Write-Host "App URL: $appUrl" -ForegroundColor Green
        Write-Host ""
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
    "share-reset" {
        Invoke-ShareReset
    }
}
