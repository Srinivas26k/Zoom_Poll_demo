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

:: Check for pip
python -m pip --version >nul 2>&1 || (
  echo ERROR: pip not available.
  pause & exit /b 1
)
echo pip is available.

:: Check architecture
python -c "import platform; import sys; sys.exit(0 if platform.architecture()[0]=='64bit' else 1)" || (
  echo WARNING: 32-bit Python detected. Some features may be limited.
)

:: Check for FFmpeg
where ffmpeg >nul 2>&1 || (
  echo WARNING: FFmpeg not found. Using alternative audio capture methods.
  echo The application will still work, but audio quality may be reduced.
  echo For better audio quality, install FFmpeg from https://ffmpeg.org/download.html
)

:: Set up virtual environment
if not exist venv (
  echo Creating virtual environment...
  python -m venv venv || (
    echo Failed to create venv.
    pause & exit /b 1
  )
)

:: Activate virtual environment
call venv\Scripts\activate || (
  echo Failed to activate venv.
  pause & exit /b 1
)
echo Virtual environment activated.

:: Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || (
  echo Dependency installation failed.
  pause & exit /b 1
)
echo Dependencies installed.

:: Set up .env
if not exist .env (
  echo No .env file found. Let's set up your Zoom credentials...
  echo.
  echo ========================================================
  echo          🔐 ZOOM API CREDENTIALS SETUP                  
  echo ========================================================
  echo.
  echo Please enter your Zoom API credentials:
  echo.
  set /p CLIENT_ID=Zoom Client ID: 
  set /p CLIENT_SECRET=Zoom Client Secret: 
  set /p REDIRECT_URI=Redirect URI (default=http://localhost:5000/oauth/callback): 
  
  if "!REDIRECT_URI!"=="" set REDIRECT_URI=http://localhost:5000/oauth/callback
  
  echo.
  echo Writing credentials to .env file...
  
  echo # Zoom API Credentials > .env
  echo CLIENT_ID=!CLIENT_ID! >> .env
  echo CLIENT_SECRET=!CLIENT_SECRET! >> .env
  echo REDIRECT_URI=!REDIRECT_URI! >> .env
  echo SECRET_TOKEN=%RANDOM%%RANDOM% >> .env
  echo LLAMA_HOST=http://localhost:11434 >> .env
  
  echo .env file created with your credentials!
) else (
  echo .env file already exists.
)

:: Deactivate virtual environment
call venv\Scripts\deactivate
echo Setup complete.

:: Finished
echo.
echo Installation completed successfully. Run start.bat to start the application.
pause
endlocal