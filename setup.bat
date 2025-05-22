@echo off
setlocal enabledelayedexpansion
title 🔧 Zoom Poll Automator – Setup

echo =======================================================
echo          ZOOM POLL AUTOMATOR - SETUP WIZARD          
echo =======================================================

:: Check for Python 3.8+
where python >nul 2>&1 || (
  echo ERROR: Python not found in PATH.
  echo Install Python 3.8+ from https://www.python.org/downloads/
  pause & exit /b 1
)

for /f "tokens=*" %%V in ('python -c "import sys;print(sys.version.split()[0])"') do set PYVER=%%V
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (set MAJOR=%%a & set MINOR=%%b)
if !MAJOR! LSS 3 (
  echo ERROR: Python 3.8+ required, found !PYVER!.
  pause & exit /b 1
)
if !MAJOR! EQU 3 if !MINOR! LSS 8 (
  echo ERROR: Python 3.8+ required, found !PYVER!.
  pause & exit /b 1
)
echo Python !PYVER! detected.

echo.
echo ================================================================================
echo  IMPORTANT: Setup is now primarily handled by menu.py.
echo  This script (setup.bat) is simplified.
echo.
echo  To complete the setup, please run:
echo.
echo    python menu.py
echo.
echo  Alternatively, you can use the PowerShell script:
echo.
echo    .\start.ps1
echo ================================================================================
echo.

:: Optionally, attempt to directly launch menu.py
echo Attempting to launch menu.py...
python menu.py

if errorlevel 1 (
    echo.
    echo Failed to automatically launch menu.py. 
    echo Please run 'python menu.py' manually.
)

pause
endlocal