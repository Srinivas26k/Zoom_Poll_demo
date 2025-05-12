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
Write-Host "--- ZOOM POLL AUTOMATOR - STARTING SETUP ---"
Write-Host ""

# 1) Python 3.8+ check
Write-Host "[1/3] Checking for Python 3.8+..."
try {
    $pythonPath = Get-Command python -ErrorAction Stop | Select-Object -ExpandProperty Source
    $pythonVersion = (python -c "import sys; print(sys.version.split()[0])").Trim()
    $majorVersion = [int]($pythonVersion.Split('.')[0])
    $minorVersion = [int]($pythonVersion.Split('.')[1])

    if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 8)) {
        Write-Host "ERROR: Python 3.8+ required, found $pythonVersion."
        Write-Host "      Please update your Python installation."
        Read-Host "Press Enter to exit..."
        exit 1
    }
    Write-Host "SUCCESS: Python $pythonVersion OK."
} catch {
    Write-Host "ERROR: Python not found in PATH."
    Write-Host "      Install Python 3.8+ -> https://www.python.org/downloads/"
    Read-Host "Press Enter to exit..."
    exit 1
}
Write-Host ""

# 2) Virtual environment
Write-Host "[2/3] Setting up virtual environment..."
$venvDir = "venv"
if (-not (Test-Path $venvDir)) {
    Write-Host "Creating virtual environment '$venvDir'..."
    try {
        python -m venv $venvDir
        Write-Host "SUCCESS: venv created."
    } catch {
        Write-Host "ERROR: Failed to create venv."
        Write-Host "      Ensure you have permission to create directories and files."
        Write-Host "      Error details: $($_.Exception.Message)"
        Read-Host "Press Enter to exit..."
        exit 1
    }
}

Write-Host "Activating virtual environment '$venvDir'..."
$activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
     Write-Host "ERROR: Activation script not found: $activateScript."
     Write-Host "     The virtual environment might not have been created correctly."
     Read-Host "Press Enter to exit..."
     exit 1
}
# Execute the activation script in the current scope
. $activateScript
if (-not $env:VIRTUAL_ENV) {
    Write-Host "ERROR: Failed to activate venv."
    Write-Host "      Check if the venv directory was created correctly."
    Read-Host "Press Enter to exit..."
    exit 1
}
Write-Host "SUCCESS: venv activated ($env:VIRTUAL_ENV)."
Write-Host ""

# 3) Install necessary packages for setup.py (rich, setuptools)
Write-Host "[3/3] Ensuring setup tools are available..."
try {
    # Install/upgrade pip, rich, and setuptools within the activated venv
    pip install --upgrade pip rich setuptools | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to install setup tools." }
    Write-Host "SUCCESS: Setup tools installed."
} catch {
    Write-Host "ERROR: Failed to install necessary packages for setup.py."
    Write-Host "      Error details: $($_.Exception.Message)"
    Read-Host "Press Enter to exit..."
    exit 1
}
Write-Host ""


# --- Run setup.py ---
Write-Host "--- Running setup.py for detailed setup steps ---"
Write-Host ""

# Execute the setup.py script
try {
    python setup.py
    if ($LASTEXITCODE -ne 0) { throw "setup.py failed." }
    Write-Host ""
    Write-Host "--- setup.py completed successfully ---"
    Write-Host ""

    # --- Launch application if setup was successful ---
    Write-Host "--- Launching Zoom Poll Automator (app.py) ---"
    Write-Host ""
    python app.py

} catch {
    Write-Host "ERROR: setup.py failed."
    Write-Host "      Please review the output above for errors during the setup process."
    Write-Host "      Error details: $($_.Exception.Message)"
    Read-Host "Press Enter to exit..."
    exit 1
}


# Deactivate venv on exit (Happens automatically when the PowerShell session ends)
# Write-Host "Deactivating virtual environment..."
# & $env:VIRTUAL_ENV\Scripts\deactivate

Write-Host ""
Write-Host "Application stopped. Press Enter to close…"
Read-Host
