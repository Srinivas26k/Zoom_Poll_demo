@echo off
title Zoom Poll Automator Launcher

:: This script launches the main PowerShell startup script (start.ps1)
:: It is designed to be double-clicked by users.

echo Launching Zoom Poll Automator setup...
echo.

:: Execute the PowerShell script
:: -NoProfile: Does not load the current user's PowerShell profile.
:: -ExecutionPolicy Bypass: Allows the script to run without changing the system's execution policy.
:: -File: Specifies the script to run.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"

echo.
echo Launcher finished. Refer to the main script window for details.
pause > nul
