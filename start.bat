@echo off
setlocal enabledelayedexpansion

:: Zoom Poll Automator Startup Script
echo =======================================================
echo           ZOOM POLL AUTOMATOR - STARTING             
echo =======================================================

:: 1) Check for venv
echo Checking for virtual environment...
if not exist venv (
    echo ERROR: Virtual environment not found.
    echo Please run setup.bat first.
    pause
    exit /b 1
)

:: 2) Check for .env
echo Checking for .env...
if not exist .env (
    if exist .env.example (
        echo Creating .env from .env.example...
        copy .env.example .env >nul
        echo WARNING: Please edit .env with your Zoom credentials before continuing.
        set /p "CONTINUE=Continue anyway? (Y/N):"
        if /I "!CONTINUE!" neq "Y" (
            pause
            exit /b 1
        )
    ) else (
        echo ERROR: No .env or .env.example found.
        echo Please run setup.bat first.
        pause
        exit /b 1
    )
) else (
    echo .env found.
)

:: 3) Check Ollama
echo Checking for Ollama...
where ollama >nul 2>&1 || (
    echo WARNING: Ollama not in PATH. Zoom polls require the Llama model.
    echo Download/install from https://ollama.ai/download
    set /p "CONTINUE=Continue anyway? (Y/N):"
    if /I "!CONTINUE!" neq "Y" (
        pause
        exit /b 1
    )
)

:: 4) Ensure logs dir
if not exist logs mkdir logs

:: 5) Activate venv and start app
echo Activating virtual environment...
call venv\\Scripts\\activate
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

echo.
echo =======================================================
echo         STARTING ZOOM POLL AUTOMATOR                 
echo =======================================================

python app.py

:: Deactivate on exit
call venv\\Scripts\\deactivate

echo.
echo Application stopped. Goodbye!
pause
endlocal