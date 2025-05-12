#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
RESET='\033[0m'

# Zoom Poll Automator Setup Script
echo -e "${CYAN}=======================================================${RESET}"
echo -e "${CYAN}          ZOOM POLL AUTOMATOR - SETUP WIZARD          ${RESET}"
echo -e "${CYAN}=======================================================${RESET}"
echo

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check for Python
echo -e "${BLUE}Checking for Python installation...${RESET}"
if ! command_exists python3; then
    echo -e "${RED}ERROR: Python not found.${RESET}"
    echo "Please install Python 3.8 or higher."
    echo "  - Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  - macOS: brew install python"
    exit 1
fi

# Verify Python version
python_version=$(python3 --version | cut -d' ' -f2)
python_major=$(echo "$python_version" | cut -d'.' -f1)
python_minor=$(echo "$python_version" | cut -d'.' -f2)

if [[ "$python_major" -lt 3 || ("$python_major" -eq 3 && "$python_minor" -lt 8) ]]; then
    echo -e "${RED}ERROR: Python 3.8+ required, found version $python_version${RESET}"
    echo "Please install a newer version of Python."
    exit 1
fi

echo -e "${GREEN}✓ Found Python $python_version ${RESET}"

# Check for pip
echo -e "${BLUE}Checking for pip...${RESET}"
if ! command_exists pip3; then
    echo -e "${RED}ERROR: pip not found${RESET}"
    echo "Please make sure pip is installed."
    echo "  - Ubuntu/Debian: sudo apt install python3-pip"
    echo "  - macOS: brew install python"
    exit 1
fi
echo -e "${GREEN}✓ Found pip ${RESET}"

# Check for FFmpeg
echo -e "${BLUE}Checking for FFmpeg...${RESET}"
if ! command_exists ffmpeg; then
    echo -e "${YELLOW}FFmpeg not found.${RESET}"
    echo "Installing FFmpeg is recommended for audio processing."
    echo "  - Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  - macOS: brew install ffmpeg"
    echo
    read -p "Do you want to continue anyway? (Y/N): " CONTINUE
    if [[ "$CONTINUE" != "Y" && "$CONTINUE" != "y" ]]; then
        echo "Setup aborted by user."
        exit 1
    fi
else
    echo -e "${GREEN}✓ Found FFmpeg ${RESET}"
fi

# Create and activate virtual environment
echo -e "${BLUE}Setting up virtual environment...${RESET}"
if [[ -d "venv" ]]; then
    echo -e "${YELLOW}Virtual environment already exists.${RESET}"
    read -p "Do you want to recreate it? (Y/N): " RECREATE
    if [[ "$RECREATE" == "Y" || "$RECREATE" == "y" ]]; then
        echo "Removing existing virtual environment..."
        rm -rf venv
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}ERROR: Failed to remove existing virtual environment.${RESET}"
            exit 1
        fi
    fi
fi

if [[ ! -d "venv" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}ERROR: Failed to create virtual environment.${RESET}"
        echo "Please ensure you have the venv module installed."
        echo "  - Ubuntu/Debian: sudo apt install python3-venv"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
if [[ $? -ne 0 ]]; then
    echo -e "${RED}ERROR: Failed to activate virtual environment.${RESET}"
    exit 1
fi

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${RESET}"
pip install --upgrade pip
if [[ $? -ne 0 ]]; then
    echo -e "${YELLOW}Warning: Failed to upgrade pip, continuing anyway.${RESET}"
fi

# Install requirements
echo -e "${BLUE}Installing dependencies...${RESET}"
pip install -r requirements.txt
if [[ $? -ne 0 ]]; then
    echo -e "${RED}ERROR: Failed to install required packages.${RESET}"
    echo "Please check your internet connection and try again."
    exit 1
fi
echo -e "${GREEN}✓ Dependencies installed successfully${RESET}"

# Check for .env file or create if needed
echo -e "${BLUE}Checking configuration...${RESET}"
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        echo "Creating .env from template..."
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env file from template${RESET}"
        echo -e "${YELLOW}You need to edit .env file with your Zoom API credentials${RESET}"
    else
        echo -e "${YELLOW}Warning: No .env or .env.example found.${RESET}"
        echo "You will need to create a .env file with your Zoom API credentials."
    fi
else
    echo -e "${GREEN}✓ .env file exists${RESET}"
fi

# Check for Ollama
echo -e "${BLUE}Checking for Ollama...${RESET}"
if ! command_exists ollama; then
    echo -e "${YELLOW}Ollama not found.${RESET}"
    echo "Please download and install Ollama from https://ollama.ai/download"
    echo "For macOS: brew install ollama"
    echo "For Linux: See https://ollama.ai/download for instructions"
else
    echo -e "${GREEN}✓ Found Ollama ${RESET}"
    
    # Check if Ollama is running
    if nc -z localhost 11434 2>/dev/null; then
        echo -e "${GREEN}✓ Ollama is running ${RESET}"
    else
        echo -e "${YELLOW}Ollama is installed but not running.${RESET}"
        echo "Please start Ollama by running 'ollama serve' in a separate terminal."
    fi
fi

# Create logs directory
echo -e "${BLUE}Creating logs directory...${RESET}"
mkdir -p logs
echo -e "${GREEN}✓ Created logs directory${RESET}"

# Make start.sh executable
echo -e "${BLUE}Making start.sh executable...${RESET}"
chmod +x start.sh
echo -e "${GREEN}✓ Made start.sh executable${RESET}"

# Setup complete
echo
echo -e "${GREEN}=======================================================${RESET}"
echo -e "${GREEN}           SETUP COMPLETED SUCCESSFULLY               ${RESET}"
echo -e "${GREEN}=======================================================${RESET}"
echo
echo "To start the application, run:"
echo -e "${CYAN}  ./start.sh${RESET}"
echo
echo -e "${YELLOW}Don't forget to edit .env file with your Zoom API credentials if you haven't already.${RESET}"
echo

# Deactivate virtual environment
deactivate

read -p "Press Enter to continue..." 