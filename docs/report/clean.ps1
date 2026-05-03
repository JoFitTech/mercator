[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $scriptDir

$extensions = @(
    '.aux', '.bbl', '.bcf', '.blg', '.fdb_latexmk', '.fls', '.log', '.out',
    '.run.xml', '.synctex.gz', '.toc', '.lof', '.lot', '.loa', '.acn', '.acr',
    '.alg', '.glg', '.glo', '.gls', '.ist'
)

$removed = 0
Get-ChildItem -Path $scriptDir -File | Where-Object {
    $name = $_.Name
    foreach ($ext in $extensions) {
        if ($name.EndsWith($ext, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
} | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Force
    $removed++
}

Write-Host "Cleanup abgeschlossen. Entfernte Dateien: $removed"
