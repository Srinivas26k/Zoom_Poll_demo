#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Start Script ---
echo "--- ZOOM POLL AUTOMATOR - INITIAL SETUP ---"
echo ""

# 1) Check for Python 3.8+
echo "[1/3] Checking for Python 3.8+..."
# Check if python3 command exists and get version
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    # Fallback to python command if python3 is not found
    if command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "ERROR: Python not found in PATH."
        echo "      Install Python 3.8+ -> https://www.python.org/downloads/"
        exit 1
    fi
fi

# Get Python version and check if it's 3.8 or higher
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR_VERSION" -lt 3 ] || ([ "$MAJOR_VERSION" -eq 3 ] && [ "$MINOR_VERSION" -lt 8 ]); then
    echo "ERROR: Python 3.8+ required, found $PYTHON_VERSION."
    echo "      Please update your Python installation."
    exit 1
fi
echo "SUCCESS: Python $PYTHON_VERSION OK."
echo ""

# 2) Virtual environment
echo "[2/3] Setting up virtual environment..."
VENV_DIR="venv"
# Check if venv directory exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment '$VENV_DIR'..."
    # Create the virtual environment using the determined Python command
    $PYTHON_CMD -m venv "$VENV_DIR" || { echo "ERROR: Failed to create venv."; exit 1; }
    echo "SUCCESS: venv created."
fi

echo "Activating virtual environment '$VENV_DIR'..."
# Source the activation script
source "$VENV_DIR/bin/activate" || { echo "ERROR: Failed to activate venv."; exit 1; }
echo "SUCCESS: venv activated ($VIRTUAL_ENV)."
echo ""

# 3) Install necessary packages for setup.py (rich, setuptools)
echo "[3/3] Ensuring setup tools are available..."
# Install/upgrade pip, rich, and setuptools within the activated venv
# Redirect output to /dev/null to keep it clean, errors will still show
pip install --upgrade pip rich setuptools > /dev/null || { echo "ERROR: Failed to install setup tools."; exit 1; }
echo "SUCCESS: Setup tools installed."
echo ""

# --- Run setup.py ---
echo "--- Running setup.py for detailed setup steps (using rich) ---"
echo ""

# Execute the setup.py script using the python executable in the activated venv
# setup.py will handle the rest of the setup and rich output
python setup.py || { echo "ERROR: setup.py failed."; exit 1; }

# setup.py will print instructions on how to run app.py if successful

# Deactivate venv on exit (Happens automatically when the script finishes)
# deactivate

echo ""
echo "Initial setup script finished. Refer to setup.py output for next steps."
echo "Press Enter to close this window…"
read -p "" # Wait for user input before closing
