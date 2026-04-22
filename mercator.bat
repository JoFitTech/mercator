@echo off
REM Mercator Control Script (cmd.exe Wrapper für mercator.ps1)
REM Verwendung: mercator.bat start|stop|restart|share-start|share-stop|share-reset

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PS1_SCRIPT=%SCRIPT_DIR%mercator.ps1"

REM Standardaktion ist "start"
set "ACTION=%1"
if "!ACTION!"=="" set "ACTION=start"

set "SERVICE=%2"
if "!SERVICE!"=="" set "SERVICE=app"

REM Führe PowerShell-Skript aus
powershell.exe -NoProfile -File "!PS1_SCRIPT!" -Action "!ACTION!" -Service "!SERVICE!"

endlocal

