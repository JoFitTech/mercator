[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

try {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location -Path $scriptDir

    if (-not (Get-Command lualatex -ErrorAction SilentlyContinue)) {
        throw "lualatex wurde nicht gefunden. Bitte MiKTeX installieren bzw. PATH prüfen."
    }

    if (-not (Get-Command biber -ErrorAction SilentlyContinue)) {
        throw "biber wurde nicht gefunden. Bitte MiKTeX installieren bzw. PATH prüfen."
    }

    Write-Host 'Starte Report-Build (LuaLaTeX + Biber)...'

    & lualatex main.tex
    if ($LASTEXITCODE -ne 0) { throw "lualatex (1. Lauf) fehlgeschlagen (Exit-Code $LASTEXITCODE)." }

    & biber main
    if ($LASTEXITCODE -ne 0) { throw "biber fehlgeschlagen (Exit-Code $LASTEXITCODE)." }

    & lualatex main.tex
    if ($LASTEXITCODE -ne 0) { throw "lualatex (2. Lauf) fehlgeschlagen (Exit-Code $LASTEXITCODE)." }

    & lualatex main.tex
    if ($LASTEXITCODE -ne 0) { throw "lualatex (3. Lauf) fehlgeschlagen (Exit-Code $LASTEXITCODE)." }

    $pdfPath = Join-Path $scriptDir 'main.pdf'
    Write-Host "Build erfolgreich. PDF: $pdfPath"
}
catch {
    Write-Error "Build fehlgeschlagen: $($_.Exception.Message)"
    exit 1
}
