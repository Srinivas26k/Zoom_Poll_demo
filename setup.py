#!/usr/bin/env python3
# setup.py - Setup script for Zoom Poll Automator

import os
import sys
import subprocess
import requests
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from dotenv import load_dotenv

console = Console()

def check_ollama():
    """Check if Ollama is running and has llama3.2 model"""
    console.print("\n[bold blue]Checking Ollama...[/]")
    
    try:
        # Check if Ollama server is running
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            console.print("[yellow]⚠️ Ollama server is not responding correctly.[/]")
            return False
            
        # Check if llama3.2 model is available
        models = response.json().get("models", [])
        llama_available = any("llama3.2" in model.get("name", "") for model in models)
        
        if llama_available:
            console.print("[green]✓ Ollama is running and llama3.2 model is available.[/]")
            return True
        else:
            console.print("[yellow]⚠️ llama3.2 model not found in Ollama.[/]")
            return False
            
    except requests.exceptions.ConnectionError:
        console.print("[yellow]⚠️ Could not connect to Ollama server.[/]")
        return False
    except Exception as e:
        console.print(f"[red]Error checking Ollama: {str(e)}[/]")
        return False

def start_ollama():
    """Start Ollama server in a new window"""
    console.print("\n[bold blue]Starting Ollama server...[/]")
    
    try:
        if sys.platform == "win32":
            # Start in new CMD window on Windows
            subprocess.Popen(["start", "cmd", "/k", "ollama", "serve"], shell=True)
        else:
            # Start in new terminal on macOS/Linux
            subprocess.Popen(["gnome-terminal", "--", "ollama", "serve"], 
                             stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        
        console.print("[green]✓ Started Ollama server in a new window.[/]")
        console.print("Waiting for Ollama server to initialize...")
        time.sleep(5)  # Wait for server to start
        return True
    except Exception as e:
        console.print(f"[red]Failed to start Ollama: {str(e)}[/]")
        console.print("Please start Ollama manually by running 'ollama serve' in a separate terminal.")
        return False

def pull_llama_model():
    """Pull llama3.2 model if not available"""
    console.print("\n[bold blue]Pulling llama3.2 model...[/]")
    
    try:
        console.print("This may take several minutes depending on your internet connection...")
        result = subprocess.run(["ollama", "pull", "llama3.2:latest"], 
                                capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("[green]✓ Successfully pulled llama3.2 model.[/]")
            return True
        else:
            console.print(f"[red]Error pulling model: {result.stderr}[/]")
            console.print("Please run 'ollama pull llama3.2:latest' manually.")
            return False
    except Exception as e:
        console.print(f"[red]Failed to pull model: {str(e)}[/]")
        return False

def download_whisper_model():
    """Ensure Whisper tiny.en model is downloaded"""
    console.print("\n[bold blue]Checking Whisper model...[/]")
    
    try:
        import whisper
        console.print("Downloading/verifying Whisper tiny.en model...")
        whisper.load_model("tiny.en")
        console.print("[green]✓ Whisper model ready.[/]")
        return True
    except ImportError:
        console.print("[red]Error: Whisper package not installed correctly.[/]")
        return False
    except Exception as e:
        console.print(f"[red]Error preparing Whisper model: {str(e)}[/]")
        return False

def setup_env_file():
    """Create or update .env file with user inputs"""
    console.print("\n[bold blue]Setting up environment configuration...[/]")
    
    # Load existing values if .env exists
    env_path = Path(".env")
    existing_values = {}
    
    if env_path.exists():
        load_dotenv()
        existing_values = {
            "CLIENT_ID": os.getenv("CLIENT_ID", ""),
            "CLIENT_SECRET": os.getenv("CLIENT_SECRET", ""),
            "REDIRECT_URI": os.getenv("REDIRECT_URI", "http://localhost:8000/oauth/callback"),
            "SECRET_TOKEN": os.getenv("SECRET_TOKEN", ""),
            "LLAMA_HOST": os.getenv("LLAMA_HOST", "http://localhost:11434")
        }
    
    # Show Zoom App setup instructions
    console.print(Panel(
        "[bold]To use this application, you need to create a Zoom OAuth App:[/]\n"
        "1. Go to https://marketplace.zoom.us/develop/create\n"
        "2. Select 'OAuth' app type\n"
        "3. Add redirect URL: [cyan]http://localhost:8000/oauth/callback[/]\n"
        "4. Add scopes: [cyan]meeting:read:meeting_transcript meeting:read:list_meetings "
        "meeting:read:poll meeting:read:token meeting:write:poll user:read:zak zoomapp:inmeeting[/]\n"
        "5. Copy your Client ID and Client Secret",
        title="Zoom API Configuration"
    ))
    
    # Get user inputs with existing values as defaults
    client_id = Prompt.ask("Enter Zoom Client ID", 
                          default=existing_values.get("CLIENT_ID", ""))
    
    client_secret = Prompt.ask("Enter Zoom Client Secret", 
                              default=existing_values.get("CLIENT_SECRET", ""))
    
    redirect_uri = Prompt.ask("Redirect URI", 
                             default=existing_values.get("REDIRECT_URI", "http://localhost:8000/oauth/callback"))
    
    # Generate random secret token if not already set
    import secrets
    secret_token = existing_values.get("SECRET_TOKEN", "") or secrets.token_hex(24)
    
    # Ollama host
    llama_host = Prompt.ask("Ollama Host", 
                           default=existing_values.get("LLAMA_HOST", "http://localhost:11434"))
    
    # Write to .env file
    with open(".env", "w") as f:
        f.write(f"CLIENT_ID={client_id}\n")
        f.write(f"CLIENT_SECRET={client_secret}\n")
        f.write(f"REDIRECT_URI={redirect_uri}\n")
        f.write(f"SECRET_TOKEN={secret_token}\n")
        f.write(f"LLAMA_HOST={llama_host}\n")
    
    # Verify the environment variables are set
    load_dotenv(override=True)
    if not os.getenv("CLIENT_ID") or not os.getenv("CLIENT_SECRET"):
        console.print("[red]Error: CLIENT_ID and CLIENT_SECRET must be set in .env file[/]")
        return False
    
    console.print("[green]✓ .env file has been created/updated.[/]")
    return True

def main():
    """Main setup function"""
    console.print(Panel("[bold]Zoom Poll Automator Setup[/]", style="blue"))
    
    # Check for Ollama
    ollama_running = check_ollama()
    if not ollama_running:
        if Confirm.ask("Would you like to start Ollama server now?"):
            start_ollama()
            # Check again after trying to start
            ollama_running = check_ollama()
            
    # Pull llama3.2 model if needed
    if ollama_running and not any("llama3.2" in model.get("name", "") 
                                 for model in requests.get("http://localhost:11434/api/tags").json().get("models", [])):
        if Confirm.ask("llama3.2 model is required. Would you like to download it now?"):
            pull_llama_model()
    
    # Check/download Whisper model
    download_whisper_model()
    
    # Setup environment
    setup_env_file()
    
    console.print("\n[bold green]✓ Setup completed! You can now run the application.[/]")
    
    # Instruct the user how to run the app
    console.print(Panel(
        "The setup is now complete! To start the application:\n\n"
        "1. Make sure Ollama is running in another terminal ('ollama serve')\n"
        "2. Run the batch file: [cyan]start_poll_automator.bat[/]\n"
        "3. Follow the instructions in the web browser",
        title="Next Steps"
    ))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())