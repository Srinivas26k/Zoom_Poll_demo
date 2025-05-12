@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo          ZOOM POLL AUTOMATOR - SETUP WIZARD          
echo =======================================================

:: 1) Check Python
echo Checking for Python 3.8+...
where python >nul 2>&1 || (
    echo ERROR: Python not found in PATH.
    echo Install Python 3.8+ and add to PATH.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%V in ('python -c "import sys; print(sys.version[:3])"') do set PYVER=%%V
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set MAJOR=%%a
    set MINOR=%%b
)
if !MAJOR! LSS 3 (
    echo ERROR: Python 3.8+ required, found !PYVER!.
    pause & exit /b 1
)
if !MAJOR! EQU 3 if !MINOR! LSS 8 (
    echo ERROR: Python 3.8+ required, found !PYVER!.
    pause & exit /b 1
)
echo ✓ Python !PYVER! detected.

:: 2) Check pip
echo Checking for pip...
python -m pip --version >nul 2>&1 || (
    echo ERROR: pip not available.
    pause & exit /b 1
)
echo ✓ pip found.

:: 3) Check FFmpeg
echo Checking for FFmpeg...
where ffmpeg >nul 2>&1 || (
    echo WARNING: FFmpeg not found. Audio processing may fail.
    echo Download from https://ffmpeg.org/download.html
    set /p "CONTINUE=Continue anyway? (Y/N):"
    if /I "!CONTINUE!" neq "Y" (
        pause & exit /b 1
    )
)
echo ✓ FFmpeg check complete.

:: 4) Create & Activate venv
echo Setting up virtual environment...
if exist venv (
    echo Virtual environment already exists.
    set /p "RECREATE=Recreate it? (Y/N):"
    if /I "!RECREATE!"=="Y" rd /S /Q venv
)
if not exist venv python -m venv venv
call venv\Scripts\activate

:: 5) Install dependencies
echo Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt || (
    echo ERROR: Failed to install Python packages.
    pause & exit /b 1
)
echo ✓ Python packages installed.

:: 6) .env file
echo Checking configuration...
if not exist .env (
    if exist .env.example (
        echo Creating .env from template...
        copy .env.example .env >nul
        echo Please edit .env with your Zoom API credentials.
    ) else (
        echo WARNING: No .env or .env.example found. Create .env manually.
    )
) else (
    echo .env already exists.
)

:: 7) Ollama check
echo Checking for Ollama...
where ollama >nul 2>&1 && echo ✓ Ollama found. || (
    echo WARNING: Ollama not in PATH.
    echo Install from https://ollama.ai/download
)

echo.
echo =======================================================
echo           SETUP COMPLETED SUCCESSFULLY               
echo =======================================================
echo To start, run start.bat
pause
endlocal