@echo off
setlocal enabledelayedexpansion
title Zoom Poll Automator Setup

:: Set colors using ANSI escape codes
set "ESC=0x1B"
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "MAGENTA=[95m"
set "CYAN=[96m"
set "WHITE=[97m"
set "RESET=[0m"

:: Header
cls
echo %ESC%%CYAN%=========================================================%ESC%%RESET%
echo %ESC%%CYAN%              ZOOM POLL AUTOMATOR - SETUP               %ESC%%RESET%
echo %ESC%%CYAN%=========================================================%ESC%%RESET%
echo.

:: Check if Python is installed
echo %ESC%%BLUE%[*] Checking if Python is installed...%ESC%%RESET%
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %ESC%%RED%[!] Python is not installed or not in PATH.%ESC%%RESET%
    echo %ESC%%YELLOW%[i] Please install Python 3.8 or newer from python.org%ESC%%RESET%
    echo %ESC%%YELLOW%[i] Make sure to check "Add Python to PATH" during installation.%ESC%%RESET%
    pause
    exit /b 1
)
echo %ESC%%GREEN%[+] Python is installed.%ESC%%RESET%

:: Check Python version
for /f "tokens=2" %%I in ('python --version 2^>^&1') do set PYTHON_VERSION=%%I
echo %ESC%%BLUE%[*] Python version: %PYTHON_VERSION%%ESC%%RESET%

:: Create virtual environment
echo.
echo %ESC%%BLUE%[*] Creating virtual environment...%ESC%%RESET%
if not exist "venv" (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo %ESC%%RED%[!] Failed to create virtual environment.%ESC%%RESET%
        echo %ESC%%YELLOW%[i] Try running: pip install virtualenv%ESC%%RESET%
        pause
        exit /b 1
    )
)
echo %ESC%%GREEN%[+] Virtual environment created.%ESC%%RESET%

:: Activate virtual environment
echo.
echo %ESC%%BLUE%[*] Activating virtual environment...%ESC%%RESET%
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo %ESC%%RED%[!] Failed to activate virtual environment.%ESC%%RESET%
    pause
    exit /b 1
)
echo %ESC%%GREEN%[+] Virtual environment activated.%ESC%%RESET%

:: Upgrade pip
echo.
echo %ESC%%BLUE%[*] Upgrading pip...%ESC%%RESET%
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo %ESC%%RED%[!] Failed to upgrade pip.%ESC%%RESET%
    pause
    exit /b 1
)
echo %ESC%%GREEN%[+] Pip upgraded.%ESC%%RESET%

:: Install requirements
echo.
echo %ESC%%BLUE%[*] Installing requirements...%ESC%%RESET%
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo %ESC%%YELLOW%[!] Some packages failed to install. Trying individual installations...%ESC%%RESET%
    
    pip install Flask>=2.0
    pip install python-dotenv>=0.21
    pip install requests>=2.25
    pip install openai>=0.27
    pip install git+https://github.com/openai/whisper.git@main
    pip install sounddevice>=0.4
    pip install soundfile>=0.11
    pip install librosa>=0.10
    pip install numpy>=1.23
    pip install rich>=12
)
echo %ESC%%GREEN%[+] Dependencies installed.%ESC%%RESET%

:: Check if Ollama is available
echo.
echo %ESC%%BLUE%[*] Checking if Ollama is installed...%ESC%%RESET%
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo %ESC%%YELLOW%[!] Ollama not found in PATH.%ESC%%RESET%
    echo %ESC%%YELLOW%[i] You'll need to install Ollama from https://ollama.com/download%ESC%%RESET%
    echo %ESC%%YELLOW%[i] After installation, run 'ollama serve' in a separate terminal.%ESC%%RESET%
    choice /C YN /M "Do you want to open the Ollama download page? (Y/N)"
    if !errorlevel! equ 1 (
        start https://ollama.com/download
    )
) else (
    echo %ESC%%GREEN%[+] Ollama is installed.%ESC%%RESET%
    
    :: Check if llama3.2 model is available
    echo %ESC%%BLUE%[*] Checking for llama3.2 model...%ESC%%RESET%
    ollama list 2>nul | findstr "llama3.2" >nul
    if %errorlevel% neq 0 (
        echo %ESC%%YELLOW%[!] llama3.2 model not found.%ESC%%RESET%
        choice /C YN /M "Do you want to download the llama3.2 model now? (Y/N)"
        if !errorlevel! equ 1 (
            echo %ESC%%BLUE%[*] Downloading llama3.2 model (this may take a while)...%ESC%%RESET%
            start /b ollama pull llama3.2:latest
            echo %ESC%%GREEN%[+] Download started in background. You can continue with setup.%ESC%%RESET%
        )
    ) else (
        echo %ESC%%GREEN%[+] llama3.2 model is available.%ESC%%RESET%
    )
)

:: Check if whisper model is downloaded
echo.
echo %ESC%%BLUE%[*] Checking for Whisper model...%ESC%%RESET%
if not exist "%USERPROFILE%\.cache\whisper" (
    echo %ESC%%YELLOW%[!] Whisper model not found. It will be downloaded on first run.%ESC%%RESET%
) else (
    echo %ESC%%GREEN%[+] Whisper cache directory exists.%ESC%%RESET%
)

:: Create .env file with user input
echo.
echo %ESC%%CYAN%=========================================================%ESC%%RESET%
echo %ESC%%CYAN%                ZOOM APP CONFIGURATION                   %ESC%%RESET%
echo %ESC%%CYAN%=========================================================%ESC%%RESET%
echo.
echo %ESC%%YELLOW%[i] You will need to create a Zoom OAuth App first.%ESC%%RESET%
echo %ESC%%YELLOW%[i] Visit: https://marketplace.zoom.us/develop/create%ESC%%RESET%
echo %ESC%%YELLOW%[i] Create OAuth app and add these redirect URLs:%ESC%%RESET%
echo %ESC%%YELLOW%    - http://localhost:8000/oauth/callback%ESC%%RESET%
echo.

:: Check if .env file already exists
if exist ".env" (
    echo %ESC%%YELLOW%[!] .env file already exists.%ESC%%RESET%
    choice /C YN /M "Do you want to overwrite it? (Y/N)"
    if !errorlevel! neq 1 (
        echo %ESC%%YELLOW%[i] Keeping existing .env file.%ESC%%RESET%
        goto :skip_env
    )
)

echo %ESC%%BLUE%[*] Creating .env file...%ESC%%RESET%

set /p CLIENT_ID=%ESC%%WHITE%Enter your Zoom Client ID: %ESC%%RESET%
set /p CLIENT_SECRET=%ESC%%WHITE%Enter your Zoom Client Secret: %ESC%%RESET%

:: Generate random SECRET_TOKEN
set "CHARS=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
set "SECRET_TOKEN="
for /L %%i in (1,1,24) do call :append_random
echo %ESC%%WHITE%Generated random SECRET_TOKEN: !SECRET_TOKEN!%ESC%%RESET%

:: Create the .env file
(
    echo CLIENT_ID=!CLIENT_ID!
    echo CLIENT_SECRET=!CLIENT_SECRET!
    echo SECRET_TOKEN=!SECRET_TOKEN!
    echo REDIRECT_URI=http://localhost:8000/oauth/callback
    echo LLAMA_HOST=http://localhost:11434
) > .env

echo %ESC%%GREEN%[+] .env file created successfully.%ESC%%RESET%

:skip_env
echo.
echo %ESC%%GREEN%[+] Setup completed successfully!%ESC%%RESET%
echo.
echo %ESC%%CYAN%=========================================================%ESC%%RESET%
echo %ESC%%CYAN%                      NEXT STEPS                         %ESC%%RESET%
echo %ESC%%CYAN%=========================================================%ESC%%RESET%
echo.
echo %ESC%%WHITE%1. Launch Ollama before starting the app:%ESC%%RESET%
echo %ESC%%YELLOW%   - Run 'ollama serve' in a separate terminal%ESC%%RESET%
echo.
echo %ESC%%WHITE%2. Run the application:%ESC%%RESET%
echo %ESC%%YELLOW%   - Execute start.bat to launch the application%ESC%%RESET%
echo %ESC%%YELLOW%   - Follow the web interface instructions%ESC%%RESET%
echo.
pause
exit /b 0

:append_random
:: Get a random character from CHARS
set /a rand=!random! %% 62
set "char=!CHARS:~%rand%,1!"
set "SECRET_TOKEN=!SECRET_TOKEN!!char!"
exit /b