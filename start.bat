@echo off
setlocal enabledelayedexpansion
title 🚀 Zoom Poll Automator – One-Click Start

:: ─────────────────────────────────────────────────────────────
:: 💡 Colors for visibility
set "GREEN=[92m" & set "YELLOW=[93m" & set "RED=[91m" & set "RESET=[0m"
:: ─────────────────────────────────────────────────────────────

echo %GREEN%========================================================%RESET%
echo %GREEN%         🚀 ZOOM POLL AUTOMATOR – STARTING              %RESET%
echo %GREEN%========================================================%RESET%
echo.

:: 1) Python 3.8+ check
where python >nul 2>&1 || (
  echo %RED%❌ ERROR: Python not found in PATH.%RESET%
  echo     Install Python 3.8+ → https://www.python.org/downloads/
  pause & exit /b 1
)
for /f "tokens=*" %%V in ('python -c "import sys;print(sys.version.split()[0])"') do set PYVER=%%V
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (set MAJOR=%%a & set MINOR=%%b)
if !MAJOR! LSS 3 (
  echo %RED%❌ ERROR: Python 3.8+ required, found !PYVER!.%RESET%
  pause & exit /b 1
)
if !MAJOR! EQU 3 if !MINOR! LSS 8 (
  echo %RED%❌ ERROR: Python 3.8+ required, found !PYVER!.%RESET%
  pause & exit /b 1
)
echo %GREEN%✓ Python !PYVER! OK.%RESET%
echo.

:: 2) pip check
python -m pip --version >nul 2>&1 || (
  echo %RED%❌ ERROR: pip not available.%RESET%
  pause & exit /b 1
)

:: 3) FFmpeg check
where ffmpeg >nul 2>&1 || (
  echo %YELLOW%WARNING: FFmpeg not found. Using alternative audio capture methods.%RESET%
  echo %YELLOW%The application will still work, but audio quality may be reduced.%RESET%
  echo %YELLOW%If you want better audio quality, install FFmpeg from https://ffmpeg.org/download.html%RESET%
)

:: 4) Virtual environment
if not exist venv (
  echo %YELLOW%Creating virtual environment...%RESET%
  python -m venv venv || (
    echo %RED%❌ Failed to create venv.%RESET%
    pause & exit /b 1
  )
)
call venv\Scripts\activate || (
  echo %RED%❌ Failed to activate venv.%RESET%
  pause & exit /b 1
)
echo %GREEN%✓ venv activated.%RESET%
echo.

:: 5) Dependencies
echo Installing/upgrading dependencies…
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt >nul 2>&1 || (
  echo %RED%❌ Dependency install failed.%RESET%
  pause & exit /b 1
)
echo %GREEN%✓ Dependencies installed.%RESET%
echo.

:: 6) Whisper model
echo Validating Whisper model…
python -c "import whisper; whisper.load_model('tiny.en')" >nul 2>&1 || (
  echo %RED%❌ Whisper model load failed.%RESET%
  pause & exit /b 1
)
echo %GREEN%✓ Whisper model ready.%RESET%
echo.

:: 7) .env setup
if not exist .env (
  echo %YELLOW%No .env file found. Let's set up your Zoom credentials...%RESET%
  echo.
  echo %GREEN%========================================================%RESET%
  echo %GREEN%         🔐 ZOOM API CREDENTIALS SETUP                  %RESET%
  echo %GREEN%========================================================%RESET%
  echo.
  echo Please enter your Zoom API credentials:
  echo.
  set /p CLIENT_ID=Zoom Client ID: 
  set /p CLIENT_SECRET=Zoom Client Secret: 
  set /p REDIRECT_URI=Redirect URI (default=http://localhost:5000/oauth/callback): 
  
  if "!REDIRECT_URI!"=="" set REDIRECT_URI=http://localhost:5000/oauth/callback
  
  echo.
  echo %YELLOW%Writing credentials to .env file...%RESET%
  
  echo # Zoom API Credentials > .env
  echo CLIENT_ID=!CLIENT_ID! >> .env
  echo CLIENT_SECRET=!CLIENT_SECRET! >> .env
  echo REDIRECT_URI=!REDIRECT_URI! >> .env
  echo SECRET_TOKEN=%RANDOM%%RANDOM% >> .env
  echo LLAMA_HOST=http://localhost:11434 >> .env
  
  echo %GREEN%✓ .env file created with your credentials!%RESET%
) else (
  echo %GREEN%✓ .env detected.%RESET%
)
echo.

:: 8) Ollama check
where ollama >nul 2>&1 || (
  echo %RED%❌ Ollama not in PATH.%RESET%
  echo     Install → https://ollama.ai/download
  pause & exit /b 1
)
echo %GREEN%✓ Ollama in PATH.%RESET%

:: 9) Ollama running?
powershell -noprofile -Command ^
  "try { $c=New-Object System.Net.Sockets.TcpClient('localhost',11434); $c.Close(); 'running' } catch { 'not_running' }" >tmp.txt
set /p OLLAMA_STATUS=<tmp.txt & del tmp.txt
if /I not "!OLLAMA_STATUS!"=="running" (
  echo %YELLOW%Starting Ollama…%RESET%
  start cmd /k "ollama serve"
  timeout /t 5 >nul
)
echo %GREEN%✓ Ollama server OK.%RESET%
echo.

:: 10) llama3.2 model
ollama list 2>nul | findstr "llama3.2" >nul
if errorlevel 1 (
  echo %YELLOW%Pulling LLaMA 3.2 model…%RESET%
  ollama pull llama3.2
)
echo %GREEN%✓ LLaMA 3.2 model ready.%RESET%
echo.

:: 11) Logs folder
if not exist logs mkdir logs
echo %GREEN%✓ Logs directory ready.%RESET%
echo.

:: 12) Launch application
echo %GREEN%========================================================%RESET%
echo %GREEN%      🚀 Launching Zoom Poll Automator (app.py)      %RESET%
echo %GREEN%========================================================%RESET%
python app.py

:: 13) Deactivate venv on exit
call venv\Scripts\deactivate

echo.
echo %YELLOW%Application stopped. Press any key to close…%RESET%
pause
endlocal
