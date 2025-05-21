<#
.SYNOPSIS
Starts the Zoom Poll Automator application by running the setup.py script.
Sets up the virtual environment and then executes setup.py for the main setup logic.
.DESCRIPTION
This script performs the following steps:
1. Checks for Python 3.8+ in the system's PATH.
2. Creates a Python virtual environment if it doesn't exist.
3. Activates the virtual environment.
4. Installs/upgrades pip and installs 'rich' and 'setuptools' in the venv
   so that setup.py can run correctly with rich output.
5. Executes the setup.py script within the activated virtual environment.
6. Launches the main application script (app.py) if setup.py was successful.
7. Deactivates the virtual environment upon script completion.
.NOTES
Requires PowerShell 5.1 or later (standard on modern Windows).
Requires Python 3.8+ installed.
The main setup logic and rich formatting are handled by the setup.py script.
Save this file with UTF-8 encoding.
#>

$ErrorActionPreference = "Stop" # Stop the script on any error

# --- Start Script ---
Write-Host "================================================"
Write-Host "      ZOOM POLL AUTOMATOR - SETUP WIZARD"
Write-Host "================================================"
Write-Host ""

# Function to handle errors consistently
function Handle-Error {
    param(
        [string]$ErrorMessage,
        [string]$Details = "",
        [string]$HelpUrl = "https://deepwiki.com/Srinivas26k/Zoom_Poll_demo/1-overview"
    )
    Write-Host "`nERROR: $ErrorMessage" -ForegroundColor Red
    if ($Details) {
        Write-Host "Details: $Details" -ForegroundColor Red
    }
    Write-Host "For help, visit: $HelpUrl" -ForegroundColor Yellow
    Write-Host "`nPress Enter to exit..."
    Read-Host
    exit 1
}

# Function to check and create Python virtual environment
function Setup-VirtualEnvironment {
    $venvDir = "venv"
    if (-not (Test-Path $venvDir)) {
        Write-Host "Creating virtual environment '$venvDir'..."
        try {
            python -m venv $venvDir
            if ($LASTEXITCODE -ne 0) { throw "Failed to create venv" }
            Write-Host "SUCCESS: Virtual environment created." -ForegroundColor Green
        } catch {
            Handle-Error "Failed to create virtual environment" $_.Exception.Message
        }
    }

    # Activate virtual environment
    $activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
    if (-not (Test-Path $activateScript)) {
        Handle-Error "Virtual environment activation script not found" "The virtual environment might be corrupted. Try deleting the 'venv' folder and running setup again."
    }

    try {
        . $activateScript
        if (-not $env:VIRTUAL_ENV) {
            Handle-Error "Failed to activate virtual environment" "Environment variable VIRTUAL_ENV not set after activation"
        }
        Write-Host "SUCCESS: Virtual environment activated." -ForegroundColor Green
    } catch {
        Handle-Error "Failed to activate virtual environment" $_.Exception.Message
    }
}

# Function to install base dependencies
function Install-BaseDependencies {
    Write-Host "`n[*] Installing base dependencies..." -ForegroundColor Cyan
    try {
        # Upgrade pip first
        python -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip" }
        Write-Host "SUCCESS: Pip upgraded." -ForegroundColor Green

        # Install base requirements needed for setup.py
        python -m pip install requests rich python-dotenv setuptools
        if ($LASTEXITCODE -ne 0) { throw "Failed to install base dependencies" }
        Write-Host "SUCCESS: Base dependencies installed." -ForegroundColor Green
    } catch {
        Handle-Error "Failed to install base dependencies" $_.Exception.Message
    }
}

# 1) Python version check
Write-Host "[1/2] Checking Python version..." -ForegroundColor Cyan
try {
    $pythonVersion = (python -c "import sys; print(sys.version.split()[0])").Trim()
    $majorVersion = [int]($pythonVersion.Split('.')[0])
    $minorVersion = [int]($pythonVersion.Split('.')[1])

    if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 8)) {
        Handle-Error "Python 3.8+ required, found $pythonVersion" "Please update your Python installation from https://www.python.org/downloads/"
    }
    Write-Host "SUCCESS: Python $pythonVersion detected." -ForegroundColor Green
} catch {
    Handle-Error "Python not found in PATH" "Install Python 3.8+ from https://www.python.org/downloads/ and ensure 'Add Python to PATH' is checked"
}

# 2) Launch menu.py
Write-Host "`n[2/2] Launching application menu..." -ForegroundColor Cyan
try {
    # Install minimal dependencies needed for menu.py
    python -m pip install rich python-dotenv
    python menu.py
    if ($LASTEXITCODE -ne 0) {
        Handle-Error "Menu.py failed to start" "The application menu encountered an error"
    }
} catch {
    Handle-Error "Failed to launch menu.py" $_.Exception.Message
}

Write-Host "`nApplication closed." -ForegroundColor Green
Write-Host "Press Enter to exit..."
Read-Host
