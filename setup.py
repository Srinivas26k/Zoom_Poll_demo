#!/usr/bin/env python3
# setup.py - Setup script for Zoom Poll Automator

import os
import sys
import subprocess
import requests
import time
import venv
import logging
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from dotenv import load_dotenv
from rich.progress import Progress, SpinnerColumn, TextColumn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("setup")
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

class SetupWizard:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.env_file = self.project_root / ".env"
        self.requirements_file = self.project_root / "requirements.txt"
    
    def check_python_version(self) -> bool:
        """Check if Python version meets requirements."""
        required_version = (3, 8)
        current_version = sys.version_info[:2]
        
        if current_version < required_version:
            console.print(f"[red]Python {required_version[0]}.{required_version[1]} or higher is required. "
                         f"Current version: {current_version[0]}.{current_version[1]}[/]")
            return False
        return True
    
    def create_virtual_environment(self) -> bool:
        """Create a Python virtual environment."""
        try:
            if self.venv_path.exists():
                if not Confirm.ask("Virtual environment already exists. Recreate?"):
                    return True
                import shutil
                shutil.rmtree(self.venv_path)
            
            console.print("Creating virtual environment...")
            venv.create(self.venv_path, with_pip=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create virtual environment: {str(e)}")
            return False
    
    def install_dependencies(self) -> bool:
        """Install required Python packages."""
        try:
            console.print("Installing dependencies...")
            
            # Determine the pip executable path
            if sys.platform == "win32":
                pip_path = self.venv_path / "Scripts" / "pip.exe"
            else:
                pip_path = self.venv_path / "bin" / "pip"
            
            # Upgrade pip
            subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)
            
            # Install requirements
            subprocess.run([str(pip_path), "install", "-r", str(self.requirements_file)], check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {str(e)}")
            return False
    
    def check_ffmpeg(self) -> bool:
        """Check if FFmpeg is installed."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[yellow]FFmpeg not found. Please install FFmpeg:[/]")
            console.print("  - Windows: Download from https://ffmpeg.org/download.html")
            console.print("  - macOS: brew install ffmpeg")
            console.print("  - Linux: sudo apt install ffmpeg")
            return False
    
    def check_ollama(self) -> bool:
        """Check if Ollama is installed and running."""
        try:
            subprocess.run(["ollama", "list"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[yellow]Ollama not found. Please install Ollama:[/]")
            console.print("  - Download from https://ollama.ai/download")
            console.print("  - After installation, run 'ollama serve' in a separate terminal")
            return False
    
    def create_env_file(self) -> bool:
        """Create .env file with user configuration."""
        try:
            if self.env_file.exists():
                if not Confirm.ask(".env file already exists. Overwrite?"):
                    return True
            
            console.print("\n[bold]Zoom API Configuration[/bold]")
            client_id = Prompt.ask("Enter your Zoom Client ID")
            client_secret = Prompt.ask("Enter your Zoom Client Secret")
            
            console.print("\n[bold]Optional Configuration[/bold]")
            llama_host = Prompt.ask(
                "Enter Ollama host URL",
                default="http://localhost:11434"
            )
            log_level = Prompt.ask(
                "Enter log level",
                choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                default="INFO"
            )
            
            # Write .env file
            env_content = f"""# Zoom API Configuration
CLIENT_ID={client_id}
CLIENT_SECRET={client_secret}
REDIRECT_URI=http://localhost:8000/oauth/callback

# Ollama Configuration
LLAMA_HOST={llama_host}

# Logging Configuration
LOG_LEVEL={log_level}
"""
            self.env_file.write_text(env_content)
            console.print("[green]✓ Created .env file[/]")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create .env file: {str(e)}")
            return False
    
    def run(self) -> bool:
        """Run the setup wizard."""
        console.print("[bold blue]Zoom Poll Automator Setup Wizard[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Check Python version
            task = progress.add_task("Checking Python version...", total=None)
            if not self.check_python_version():
                return False
            progress.update(task, completed=True)
            
            # Create virtual environment
            task = progress.add_task("Creating virtual environment...", total=None)
            if not self.create_virtual_environment():
                return False
            progress.update(task, completed=True)
            
            # Install dependencies
            task = progress.add_task("Installing dependencies...", total=None)
            if not self.install_dependencies():
                return False
            progress.update(task, completed=True)
            
            # Check FFmpeg
            task = progress.add_task("Checking FFmpeg...", total=None)
            if not self.check_ffmpeg():
                return False
            progress.update(task, completed=True)
            
            # Check Ollama
            task = progress.add_task("Checking Ollama...", total=None)
            if not self.check_ollama():
                return False
            progress.update(task, completed=True)
            
            # Create .env file
            task = progress.add_task("Creating configuration...", total=None)
            if not self.create_env_file():
                return False
            progress.update(task, completed=True)
        
        console.print("\n[bold green]✓ Setup completed successfully![/bold green]")
        console.print("\nTo start the application:")
        console.print("1. Activate the virtual environment:")
        if sys.platform == "win32":
            console.print("   venv\\Scripts\\activate")
        else:
            console.print("   source venv/bin/activate")
        console.print("2. Run the application:")
        console.print("   python app.py")
        
        return True

def main():
    """Entry point for the setup script."""
    try:
        wizard = SetupWizard()
        success = wizard.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Setup failed: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()