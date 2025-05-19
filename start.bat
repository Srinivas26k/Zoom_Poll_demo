@echo off
echo Starting Zoom Poll Automator...

REM Check for Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Create and activate virtual environment
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

REM Install/upgrade pip and dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Run the application
echo Starting application...
python app.py

REM Keep window open on error
if errorlevel 1 (
    echo Application stopped with an error
    pause
)