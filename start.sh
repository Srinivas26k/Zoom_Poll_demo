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

# Zoom Poll Automator Start Script
echo -e "${CYAN}=======================================================${RESET}"
echo -e "${CYAN}           ZOOM POLL AUTOMATOR - STARTING             ${RESET}"
echo -e "${CYAN}=======================================================${RESET}"
echo

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check for virtual environment
echo -e "${BLUE}Checking virtual environment...${RESET}"
if [[ ! -d "venv" ]]; then
    echo -e "${RED}ERROR: Virtual environment not found.${RESET}"
    echo "Please run ./setup.sh first to configure the application."
    echo
    read -p "Press Enter to continue..."
    exit 1
fi

# Check for .env file
echo -e "${BLUE}Checking configuration...${RESET}"
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example...${RESET}"
        cp .env.example .env
        echo -e "${GREEN}Created .env file from template${RESET}"
        echo -e "${YELLOW}You should edit the .env file with your Zoom API credentials before continuing.${RESET}"
        read -p "Do you want to continue anyway? (Y/N): " CONTINUE
        if [[ "$CONTINUE" != "Y" && "$CONTINUE" != "y" ]]; then
            exit 1
        fi
    else
        echo -e "${RED}ERROR: No .env or .env.example file found.${RESET}"
        echo "Please run ./setup.sh first to configure the application."
        echo
        read -p "Press Enter to continue..."
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env file found${RESET}"
fi

# Check for Ollama
echo -e "${BLUE}Checking for Ollama...${RESET}"
if ! command_exists ollama; then
    echo -e "${YELLOW}Warning: Ollama not found.${RESET}"
    echo "This application requires Ollama for LLaMA 3.2 model inference."
    echo "Please install Ollama from https://ollama.ai/download"
    read -p "Do you want to continue anyway? (Y/N): " CONTINUE
    if [[ "$CONTINUE" != "Y" && "$CONTINUE" != "y" ]]; then
        exit 1
    fi
else
    # Check if Ollama is running
    if nc -z localhost 11434 2>/dev/null; then
        echo -e "${GREEN}✓ Ollama is running${RESET}"
    else
        echo -e "${YELLOW}Warning: Ollama is installed but not running.${RESET}"
        
        read -p "Do you want to start Ollama now? (Y/N): " START_OLLAMA
        if [[ "$START_OLLAMA" == "Y" || "$START_OLLAMA" == "y" ]]; then
            echo "Starting Ollama in a new terminal..."
            
            # Platform-specific terminal launching
            if [[ "$(uname)" == "Darwin" ]]; then
                # macOS
                osascript -e 'tell app "Terminal" to do script "ollama serve"' &
            elif command_exists gnome-terminal; then
                # Linux with GNOME
                gnome-terminal -- bash -c "ollama serve" &
            elif command_exists xterm; then
                # Linux with X11
                xterm -e "ollama serve" &
            else
                # Generic approach
                echo -e "${YELLOW}Could not launch terminal automatically.${RESET}"
                echo "Please start Ollama manually by running 'ollama serve' in another terminal."
                read -p "Do you want to continue anyway? (Y/N): " CONTINUE
                if [[ "$CONTINUE" != "Y" && "$CONTINUE" != "y" ]]; then
                    exit 1
                fi
            fi
            
            echo "Waiting for Ollama to start..."
            # Try to connect to Ollama for up to 10 seconds
            for i in {1..10}; do
                if nc -z localhost 11434 2>/dev/null; then
                    echo -e "${GREEN}✓ Ollama started successfully${RESET}"
                    break
                fi
                sleep 1
                if [[ $i -eq 10 ]]; then
                    echo -e "${YELLOW}Warning: Failed to verify Ollama startup.${RESET}"
                    echo "Make sure Ollama is running before proceeding."
                    read -p "Do you want to continue anyway? (Y/N): " CONTINUE
                    if [[ "$CONTINUE" != "Y" && "$CONTINUE" != "y" ]]; then
                        exit 1
                    fi
                fi
            done
        else
            echo -e "${YELLOW}Continuing without Ollama...${RESET}"
            echo "The application may not function correctly without Ollama running."
            read -p "Do you want to continue anyway? (Y/N): " CONTINUE
            if [[ "$CONTINUE" != "Y" && "$CONTINUE" != "y" ]]; then
                exit 1
            fi
        fi
    fi
    
    # Check for LLaMA 3.2 model if Ollama is running
    if nc -z localhost 11434 2>/dev/null; then
        echo -e "${BLUE}Checking for LLaMA 3.2 model...${RESET}"
        if ! ollama list 2>/dev/null | grep -q "llama3.2"; then
            echo -e "${YELLOW}Warning: LLaMA 3.2 model not found.${RESET}"
            
            read -p "Do you want to download LLaMA 3.2 model now? (Y/N): " DOWNLOAD_MODEL
            if [[ "$DOWNLOAD_MODEL" == "Y" || "$DOWNLOAD_MODEL" == "y" ]]; then
                echo "Downloading LLaMA 3.2 model... This may take several minutes."
                ollama pull llama3.2
                
                echo -e "${GREEN}✓ LLaMA 3.2 model download completed${RESET}"
            else
                echo -e "${YELLOW}Continuing without LLaMA 3.2 model...${RESET}"
                echo "The application may not function correctly without the model."
                read -p "Do you want to continue anyway? (Y/N): " CONTINUE
                if [[ "$CONTINUE" != "Y" && "$CONTINUE" != "y" ]]; then
                    exit 1
                fi
            fi
        else
            echo -e "${GREEN}✓ LLaMA 3.2 model found${RESET}"
        fi
    fi
fi

# Create logs directory
echo -e "${BLUE}Creating logs directory...${RESET}"
mkdir -p logs
echo -e "${GREEN}✓ Logs directory exists${RESET}"

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${RESET}"
source venv/bin/activate
if [[ $? -ne 0 ]]; then
    echo -e "${RED}ERROR: Failed to activate virtual environment.${RESET}"
    read -p "Press Enter to continue..."
    exit 1
fi
echo -e "${GREEN}✓ Virtual environment activated${RESET}"

# Start the application
echo
echo -e "${GREEN}=======================================================${RESET}"
echo -e "${GREEN}         STARTING ZOOM POLL AUTOMATOR                 ${RESET}"
echo -e "${GREEN}=======================================================${RESET}"
echo
echo "Press Ctrl+C to stop the application."
echo

# Start the Flask application
python app.py

# Deactivate virtual environment on exit
deactivate

echo
echo -e "${CYAN}Application stopped. Goodbye!${RESET}" 