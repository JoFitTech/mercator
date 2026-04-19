@echo off
REM Mercator Control Script (cmd.exe Wrapper für mercator.ps1)
REM Verwendung: mercator.bat start|stop|restart|status|logs|init-db|open|cleanup|doctor|e2e-install|e2e-smoke|e2e

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PS1_SCRIPT=%SCRIPT_DIR%mercator.ps1"

REM Standardaktion ist "status"
set "ACTION=%1"
if "!ACTION!"=="" set "ACTION=status"

set "SERVICE=%2"
if "!SERVICE!"=="" set "SERVICE=app"

REM Führe PowerShell-Skript aus
powershell.exe -NoProfile -File "!PS1_SCRIPT!" -Action "!ACTION!" -Service "!SERVICE!"

endlocal

