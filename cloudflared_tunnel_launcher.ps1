param(
    [int]$Port = 8501,
    [int]$MaxRetries = 4,
    [int]$RetryDelaySeconds = 4,
    [int]$RegisterTimeoutSeconds = 30,
    [int]$PublicHealthRetries = 10,
    [int]$PublicHealthDelaySeconds = 2,
    [string[]]$Protocols = @("http2", "quic")
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$cloudflaredPath = Join-Path $root "cloudflared.exe"
$logFile = Join-Path $root "tunnel_launcher.log"
$publicUrlFile = Join-Path $root "PUBLIC_TUNNEL_URL.txt"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp | $Message" | Tee-Object -FilePath $logFile -Append
}

function Get-TunnelUrlFromText {
    param([string]$Text)
    if (-not $Text) { return $null }
    $m = [regex]::Match($Text, 'https://[a-z0-9\-]+\.trycloudflare\.com')
    if ($m.Success) { return $m.Value }
    return $null
}

function Test-LocalHealth {
    param([int]$TargetPort)
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$TargetPort/_stcore/health" -TimeoutSec 8
        return ($resp.StatusCode -eq 200 -and $resp.Content -match "ok")
    }
    catch {
        return $false
    }
}

function Test-PublicHealth {
    param(
        [string]$BaseUrl,
        [int]$Retries,
        [int]$DelaySeconds
    )

    for ($i = 1; $i -le $Retries; $i++) {
        try {
            $resp = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/_stcore/health" -TimeoutSec 10
            if ($resp.StatusCode -eq 200 -and $resp.Content -match "ok") {
                Write-Log "Public health OK in try $i for $BaseUrl"
                return $true
            }
        }
        catch {
            Write-Log "Public health try $i failed: $($_.Exception.Message)"
        }
        Start-Sleep -Seconds $DelaySeconds
    }
    return $false
}

if (-not (Test-Path $cloudflaredPath)) {
    throw "cloudflared not found: $cloudflaredPath"
}

Write-Log "=========================================="
Write-Log "CLOUDFLARE QUICK TUNNEL LAUNCH"
Write-Log "Target local app: http://127.0.0.1:$Port"
Write-Log "cloudflared: $cloudflaredPath"
Write-Log "=========================================="

if (-not (Test-LocalHealth -TargetPort $Port)) {
    Write-Log "Warning: local health endpoint is not OK yet on port $Port"
}
else {
    Write-Log "Local health endpoint is OK"
}

Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

$tunnelUrl = $null
$activePid = $null

for ($attempt = 1; $attempt -le $MaxRetries -and -not $tunnelUrl; $attempt++) {
    foreach ($protocol in $Protocols) {
        $outLog = Join-Path $root ("cloudflared_attempt_{0}_{1}.out.log" -f $attempt, $protocol)
        $errLog = Join-Path $root ("cloudflared_attempt_{0}_{1}.err.log" -f $attempt, $protocol)
        Remove-Item $outLog, $errLog -ErrorAction SilentlyContinue

        Write-Log "Attempt $attempt/$MaxRetries with protocol=$protocol"

        $proc = Start-Process -FilePath $cloudflaredPath `
            -ArgumentList @("tunnel", "--url", "http://127.0.0.1:$Port", "--protocol", $protocol, "--loglevel", "info") `
            -RedirectStandardOutput $outLog `
            -RedirectStandardError $errLog `
            -PassThru

        $urlFromLog = $null
        for ($wait = 1; $wait -le $RegisterTimeoutSeconds; $wait++) {
            Start-Sleep -Seconds 1

            $combined = ""
            if (Test-Path $outLog) { $combined += (Get-Content $outLog -Raw -ErrorAction SilentlyContinue) + "`n" }
            if (Test-Path $errLog) { $combined += (Get-Content $errLog -Raw -ErrorAction SilentlyContinue) }

            $urlFromLog = Get-TunnelUrlFromText -Text $combined
            if ($urlFromLog) {
                Write-Log "URL discovered after $wait s: $urlFromLog"
                break
            }

            if ($proc.HasExited) {
                Write-Log "cloudflared exited early (code=$($proc.ExitCode))"
                break
            }
        }

        if (-not $urlFromLog) {
            if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
            Write-Log "No URL found for attempt=$attempt protocol=$protocol"
            continue
        }

        if (Test-PublicHealth -BaseUrl $urlFromLog -Retries $PublicHealthRetries -DelaySeconds $PublicHealthDelaySeconds) {
            $tunnelUrl = $urlFromLog
            $activePid = $proc.Id
            Set-Content -Path $publicUrlFile -Value "$tunnelUrl`r`n" -Encoding Ascii
            Write-Log "PUBLIC_TUNNEL_URL updated: $publicUrlFile"
            break
        }

        Write-Log "Public URL not healthy, stopping process PID=$($proc.Id)"
        if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
        Start-Sleep -Seconds 1
    }

    if (-not $tunnelUrl -and $attempt -lt $MaxRetries) {
        Write-Log "Waiting $RetryDelaySeconds s before next retry round"
        Start-Sleep -Seconds $RetryDelaySeconds
    }
}

if (-not $tunnelUrl) {
    Write-Log "FAILED: could not establish a reachable Cloudflare tunnel"
    exit 1
}

Write-Log "SUCCESS: Cloudflare tunnel is reachable"
Write-Log "URL: $tunnelUrl"
Write-Log "cloudflared PID: $activePid"
Write-Output "TUNNEL_OK $tunnelUrl"



