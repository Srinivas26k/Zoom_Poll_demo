@echo off
setlocal enabledelayedexpansion

REM Enable ANSI escape sequences
reg add HKEY_CURRENT_USER\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

REM Set colors using ANSI escape codes
set "ESC="
set "GREEN=92"
set "YELLOW=93"
set "RED=91"
set "BLUE=94"
set "MAGENTA=95"
set "CYAN=96"
set "WHITE=97"
set "RESET=0"
set "BOLD=1"

REM Function to print colored text
call :initColorPrint

REM Header
cls
call :colorPrint %CYAN% %BOLD% "========================================================="
call :colorPrint %CYAN% %BOLD% "               ZOOM POLL AUTOMATOR                      "
call :colorPrint %CYAN% %BOLD% "========================================================="
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    call :colorPrint %RED% 0 "[!] Python is not installed or not in PATH."
    call :colorPrint %YELLOW% 0 "[i] Please install Python 3.8 or higher from https://www.python.org/downloads/"
    call :colorPrint %YELLOW% 0 "[i] Make sure to check 'Add Python to PATH' during installation."
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    call :colorPrint %YELLOW% 0 "[i] First time setup..."
    echo.
    python setup.py
    if errorlevel 1 (
        call :colorPrint %RED% 0 "[!] Setup failed. Please check the error messages above."
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call :colorPrint %BLUE% 0 "[*] Activating virtual environment..."
call venv\Scripts\activate.bat
if errorlevel 1 (
    call :colorPrint %RED% 0 "[!] Failed to activate virtual environment."
    pause
    exit /b 1
)
call :colorPrint %GREEN% 0 "[+] Virtual environment activated."

REM Check for .env file
if not exist ".env" (
    call :colorPrint %RED% 0 "[!] Configuration file not found."
    call :colorPrint %YELLOW% 0 "[i] Running setup to create configuration..."
    python setup.py
    if errorlevel 1 (
        call :colorPrint %RED% 0 "[!] Setup failed. Please check the errors above."
        pause
        exit /b 1
    )
)

REM Check for Ollama
echo.
call :colorPrint %BLUE% 0 "[*] Checking Ollama connection..."
curl -s http://localhost:11434/api/tags > nul
if errorlevel 1 (
    call :colorPrint %RED% 0 "[!] Cannot connect to Ollama."
    call :colorPrint %YELLOW% 0 "[i] Make sure Ollama is running with 'ollama serve' in another terminal."
    
    choice /C YN /M "Do you want to try starting Ollama now? (Y/N)"
    if !errorlevel! equ 1 (
        call :colorPrint %BLUE% 0 "[*] Starting Ollama in a new window..."
        start "Ollama Server" cmd /c "echo Starting Ollama Server... && ollama serve"
        call :colorPrint %YELLOW% 0 "[i] Waiting for Ollama to start up..."
        timeout /t 5 /nobreak > nul
        
        REM Check again after starting
        curl -s http://localhost:11434/api/tags > nul
        if errorlevel 1 (
            call :colorPrint %RED% 0 "[!] Still cannot connect to Ollama."
            call :colorPrint %YELLOW% 0 "[i] Please start Ollama manually and try again."
            pause
            exit /b 1
        )
    ) else (
        call :colorPrint %YELLOW% 0 "[i] Please start Ollama manually and try again."
        pause
        exit /b 1
    )
)
call :colorPrint %GREEN% 0 "[+] Ollama connection successful."

REM Check required llama model - Automatic download without prompting
echo.
call :colorPrint %BLUE% 0 "[*] Verifying llama3.2 model..."

REM Use ollama list instead of curl to check for model
ollama list 2>nul | findstr "llama3.2" > nul

if errorlevel 1 (
    call :colorPrint %YELLOW% 0 "[!] llama3.2 model not found."
    call :colorPrint %BLUE% 0 "[*] Automatically downloading llama3.2 model... This might take several minutes."
    call :colorPrint %YELLOW% 0 "[i] Please do not close this window."
    
    REM Run in foreground to ensure completion before continuing
    ollama pull llama3.2:latest
    
    if errorlevel 1 (
        call :colorPrint %RED% 0 "[!] Failed to download llama3.2 model."
        call :colorPrint %YELLOW% 0 "[i] The application may not work correctly without the model."
        timeout /t 5 /nobreak > nul
    ) else (
        call :colorPrint %GREEN% 0 "[+] Successfully downloaded llama3.2 model."
    )
) else (
    call :colorPrint %GREEN% 0 "[+] llama3.2 model is available."
)

REM Start the Flask application
echo.
call :colorPrint %BLUE% 0 "[*] Starting Zoom Poll Automator..."
call :colorPrint %CYAN% 0 "========================================================="
call :colorPrint %GREEN% 0 "[+] Access the web interface at: http://localhost:8000"
call :colorPrint %CYAN% 0 "========================================================="
echo.
call :colorPrint %YELLOW% 0 "[i] IMPORTANT: Press Ctrl+C to stop the application when done."
echo.

REM Start the Flask application - Use app.py directly instead of the non-existent zoom-poll
python app.py
if errorlevel 1 (
    call :colorPrint %RED% 0 "[!] Application crashed. Please check the errors above."
    pause
    exit /b 1
)

:end
deactivate
echo.
call :colorPrint %GREEN% 0 "Application stopped."
pause
exit /b 0

:initColorPrint
set "ESC="
exit /b 0

:colorPrint
set "color=%~1"
set "style=%~2"
set "text=%~3"
echo %ESC%[%style%m%ESC%[%color%m%text%%ESC%[%RESET%m
exit /b 0