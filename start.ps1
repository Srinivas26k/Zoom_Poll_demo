<#
.SYNOPSIS
Starts the Zoom Poll Automator with enhanced features and UI
#>

$ErrorActionPreference = "Stop"

Write-Host "--- ZOOM POLL AUTOMATOR ---" -ForegroundColor Blue
Write-Host ""

# Check Python version
Write-Host "[1/4] Checking Python installation..." -NoNewline
try {
    $pythonVersion = (python -c "import sys; print(sys.version.split()[0])") 2>$null
    $versionParts = $pythonVersion.Split('.')
    if ([int]$versionParts[0] -lt 3 -or ([int]$versionParts[0] -eq 3 -and [int]$versionParts[1] -lt 8)) {
        throw "Python 3.8+ required (found $pythonVersion)"
    }
    Write-Host " OK" -ForegroundColor Green
} catch {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host "Error: Python 3.8 or higher is required"
    Write-Host "Download from: https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}

# Setup virtual environment
Write-Host "[2/4] Setting up virtual environment..." -NoNewline
try {
    if (-not (Test-Path "venv")) {
        python -m venv venv
    }
    . .\venv\Scripts\Activate.ps1
    Write-Host " OK" -ForegroundColor Green
} catch {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host "Error: Failed to create/activate virtual environment"
    Read-Host "Press Enter to exit"
    exit 1
}

# Install dependencies
Write-Host "[3/4] Installing dependencies..." -NoNewline
try {
    python -m pip install --upgrade pip | Out-Null
    pip install -r requirements.txt | Out-Null
    Write-Host " OK" -ForegroundColor Green
} catch {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host "Error: Failed to install dependencies"
    Read-Host "Press Enter to exit"
    exit 1
}

# Start application
Write-Host "[4/4] Starting application..." -ForegroundColor Blue
Write-Host ""
try {
    python app.py
} catch {
    Write-Host "Error: Application crashed" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host "Press Enter to exit"
    exit 1
}