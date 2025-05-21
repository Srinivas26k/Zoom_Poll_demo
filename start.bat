@echo off
title Zoom Poll Automator Launcher

:: This script launches the main PowerShell startup script (start.ps1)
:: It is designed to be double-clicked by users.

echo ================================================
echo      Zoom Poll Automator - Setup Launcher
echo ================================================
echo.

:: Check if PowerShell is available
where powershell.exe >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: PowerShell is not installed or not in PATH.
    echo Please install PowerShell to run this application.
    echo Visit: https://docs.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows
    echo.
    pause
    exit /b 1
)

:: Check if Python is available
where python.exe >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8 or later from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Execute the PowerShell script with elevated privileges if needed
echo Launching setup process...
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Setup process failed.
    echo Please check the PowerShell window for details.
    echo If you need help, visit our documentation at:
    echo https://deepwiki.com/Srinivas26k/Zoom_Poll_demo/1-overview
    echo.
    pause
    exit /b 1
)

echo.
echo Setup completed successfully!
echo The application window should be open.
echo If you need to restart the application, run this launcher again.
echo.
pause