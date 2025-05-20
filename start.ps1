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
        [string]$Details = ""
    )
    Write-Host "`nERROR: $ErrorMessage" -ForegroundColor Red
    if ($Details) {
        Write-Host "Details: $Details" -ForegroundColor Red
    }
    Write-Host "`nPress Enter to exit..."
    Read-Host
    exit 1
}

# 1) Python 3.8+ check
Write-Host "[1/3] Checking for Python 3.8+..." -ForegroundColor Cyan
try {
    $pythonPath = Get-Command python -ErrorAction Stop | Select-Object -ExpandProperty Source
    $pythonVersion = (python -c "import sys; print(sys.version.split()[0])").Trim()
    $majorVersion = [int]($pythonVersion.Split('.')[0])
    $minorVersion = [int]($pythonVersion.Split('.')[1])

    if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 8)) {
        Handle-Error "Python 3.8+ required, found $pythonVersion" "Please update your Python installation."
    }
    Write-Host "SUCCESS: Python $pythonVersion OK." -ForegroundColor Green
} catch {
    Handle-Error "Python not found in PATH" "Install Python 3.8+ from https://www.python.org/downloads/"
}
Write-Host ""

# 2) Virtual environment
Write-Host "[2/3] Setting up virtual environment..." -ForegroundColor Cyan
$venvDir = "venv"
if (-not (Test-Path $venvDir)) {
    Write-Host "Creating virtual environment '$venvDir'..."
    try {
        python -m venv $venvDir
        if ($LASTEXITCODE -ne 0) { throw "Failed to create venv" }
        Write-Host "SUCCESS: venv created." -ForegroundColor Green
    } catch {
        Handle-Error "Failed to create venv" "Ensure you have permission to create directories and files. Error: $($_.Exception.Message)"
    }
}

Write-Host "Activating virtual environment '$venvDir'..."
$activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Handle-Error "Activation script not found" "The virtual environment might not have been created correctly. Path: $activateScript"
}

# Execute the activation script in the current scope
try {
. $activateScript
if (-not $env:VIRTUAL_ENV) {
        Handle-Error "Failed to activate venv" "Check if the venv directory was created correctly."
}
    Write-Host "SUCCESS: venv activated ($env:VIRTUAL_ENV)." -ForegroundColor Green
} catch {
    Handle-Error "Failed to activate virtual environment" $_.Exception.Message
}
Write-Host ""

# 3) Install necessary packages for setup.py
Write-Host "[3/3] Ensuring setup tools are available..." -ForegroundColor Cyan
try {
    Write-Host "Installing/upgrading required packages..."
    python -m pip install --upgrade pip rich setuptools requests python-dotenv
    if ($LASTEXITCODE -ne 0) { throw "Failed to install setup tools" }
    Write-Host "SUCCESS: Setup tools installed." -ForegroundColor Green
} catch {
    Handle-Error "Failed to install necessary packages" $_.Exception.Message
}
Write-Host ""

# --- Run setup.py ---
Write-Host "================================================"
Write-Host "      Running setup.py for detailed setup"
Write-Host "================================================"
Write-Host ""

# Execute the setup.py script
try {
    python setup.py
    if ($LASTEXITCODE -ne 0) { throw "setup.py failed" }
    Write-Host "`nSUCCESS: setup.py completed successfully" -ForegroundColor Green
    Write-Host ""

    # --- Launch application if setup was successful ---
    Write-Host "================================================"
    Write-Host "      Launching Zoom Poll Automator"
    Write-Host "================================================"
    Write-Host ""
    python app.py

} catch {
    Handle-Error "Setup process failed" "Please review the output above for errors during the setup process. Error: $($_.Exception.Message)"
}

Write-Host "`nApplication stopped. Press Enter to close…"
Read-Host
