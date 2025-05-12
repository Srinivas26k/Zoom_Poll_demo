#!/usr/bin/env python3
# setup.py - Setup script for Zoom Poll Automator

import os
import sys
import subprocess
import requests
import time
import logging
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from dotenv import load_dotenv
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live # Import Live for dynamic updates
import secrets # Import secrets for generating Flask Secret Key

# Configure logging (optional, rich handles most user-facing output)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("setup")
console = Console()

class SetupWizard:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.env_file = self.project_root / ".env"
        self.requirements_file = self.project_root / "requirements.txt"
        # Assume running within the activated venv, determine pip path dynamically
        if sys.platform == "win32":
            self.pip_path = self.venv_path / "Scripts" / "pip.exe"
        else:
            self.pip_path = self.venv_path / "bin" / "pip"

    def check_dependencies_installed(self) -> bool:
        """Check if core dependencies are installed."""
        try:
            # Try importing a few key packages
            import torch
            import openai
            import rich
            # If imports succeed, assume dependencies are mostly there
            return True
        except ImportError:
            return False

    def install_dependencies(self, progress: Progress) -> bool:
        """Install required Python packages."""
        task_id = progress.add_task("[bold blue]Installing dependencies...", total=None)
        try:
            # Upgrade pip first
            progress.update(task_id, description="[bold blue]Upgrading pip...")
            subprocess.run([str(self.pip_path), "install", "--upgrade", "pip"], check=True, capture_output=True)

            # Install requirements - output is captured to prevent clutter, errors will still raise
            progress.update(task_id, description="[bold blue]Installing dependencies from requirements.txt...")
            # Install openai-whisper separately first as it caused issues before
            subprocess.run([str(self.pip_path), "install", "git+https://github.com/openai/whisper.git"], check=True, capture_output=True)
            # Install the rest, skipping openai-whisper dependencies to avoid conflicts
            subprocess.run([str(self.pip_path), "install", "--no-deps", "-r", str(self.requirements_file)], check=True, capture_output=True)

            progress.update(task_id, description="[bold green]Dependencies installed.")
            progress.remove_task(task_id)
            return True
        except subprocess.CalledProcessError as e:
            progress.update(task_id, description="[bold red]Dependency installation failed.")
            progress.remove_task(task_id)
            console.print(f"[red]Failed to install dependencies: {e.stderr.decode()}[/]")
            return False
        except Exception as e:
            progress.update(task_id, description="[bold red]Dependency installation failed.")
            progress.remove_task(task_id)
            console.print(f"[red]An unexpected error occurred during dependency installation: {str(e)}[/]")
            return False

    def check_ffmpeg(self, progress: Progress) -> bool:
        """Check if FFmpeg is installed."""
        task_id = progress.add_task("[bold blue]Checking FFmpeg...", total=None)
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            progress.update(task_id, description="[bold green]FFmpeg found.")
            progress.remove_task(task_id)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            progress.update(task_id, description="[bold yellow]FFmpeg not found.")
            progress.remove_task(task_id)
            console.print("[yellow]FFmpeg not found. Please install FFmpeg:[/]")
            console.print("  - Windows: Download from https://ffmpeg.org/download.html")
            console.print("  - macOS: brew install ffmpeg")
            console.print("  - Linux: sudo apt install ffmpeg")
            return False

    def check_ollama(self, progress: Progress) -> bool:
        """Check if Ollama is installed, running, and has llama3.2 model."""
        task_id = progress.add_task("[bold blue]Checking Ollama...", total=None)
        ollama_in_path = False
        try:
            subprocess.run(["ollama", "list"], capture_output=True, check=True)
            ollama_in_path = True
        except (subprocess.CalledProcessError, FileNotFoundError):
             progress.update(task_id, description="[bold red]Ollama not found in PATH.")
             progress.remove_task(task_id)
             console.print("[red]Ollama not found in PATH. Please install Ollama:[/]")
             console.print("  - Download from https://ollama.ai/download and ensure it's added to your system's PATH.")
             return False

        # If Ollama is in PATH, check if running and model is available
        try:
            progress.update(task_id, description="[bold blue]Checking Ollama server and model...")
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code != 200:
                progress.update(task_id, description="[bold yellow]Ollama server not responding.")
                progress.remove_task(task_id)
                console.print("[yellow]⚠️ Ollama server is not responding correctly.[/]")
                console.print("Please ensure Ollama server is running (run 'ollama serve' in a separate terminal).")
                return False

            models = response.json().get("models", [])
            llama_available = any("llama3.2" in model.get("name", "") for model in models)

            if llama_available:
                progress.update(task_id, description="[bold green]Ollama server OK, llama3.2 model available.")
                progress.remove_task(task_id)
                return True
            else:
                progress.update(task_id, description="[bold yellow]llama3.2 model not found.")
                progress.remove_task(task_id)
                console.print("[yellow]⚠️ llama3.2 model not found in Ollama.[/]")
                console.print("Attempting to pull the model...")
                if self.pull_llama_model():
                     console.print("[green]✓ llama3.2 model pulled successfully.[/]")
                     return True
                else:
                     console.print("[red]Failed to pull llama3.2 model.[/]")
                     return False

        except requests.exceptions.ConnectionError:
            progress.update(task_id, description="[bold yellow]Could not connect to Ollama server.")
            progress.remove_task(task_id)
            console.print("[yellow]⚠️ Could not connect to Ollama server.[/]")
            console.print("Please ensure Ollama server is running (run 'ollama serve' in a separate terminal).")
            return False
        except Exception as e:
            progress.update(task_id, description="[bold red]Error checking Ollama.")
            progress.remove_task(task_id)
            console.print(f"[red]Error checking Ollama: {str(e)}[/]")
            return False

    def pull_llama_model(self) -> bool:
        """Pull llama3.2 model if not available, with progress."""
        try:
            # Use Live to show ollama pull progress if needed
            with Live(console=console, refresh_per_second=10) as live:
                 live.update("[bold blue]Pulling llama3.2 model... (This may take time)")
                 result = subprocess.run(["ollama", "pull", "llama3.2:latest"], check=True, capture_output=True, text=True)
                 live.update("[bold green]✓ Successfully pulled llama3.2 model.")
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error pulling model: {e.stderr}[/]")
            console.print("Please run 'ollama pull llama3.2:latest' manually.")
            return False
        except Exception as e:
            console.print(f"[red]Failed to pull model: {str(e)}[/]")
            return False


    def download_whisper_model(self, progress: Progress) -> bool:
        """Ensure Whisper tiny.en model is downloaded."""
        task_id = progress.add_task("[bold blue]Checking Whisper model...", total=None)
        try:
            import whisper
            # whisper.load_model handles download/caching internally
            progress.update(task_id, description="[bold blue]Downloading/verifying Whisper tiny.en model...")
            # Whisper doesn't provide easy progress for load_model, so we just wait
            whisper.load_model("tiny.en")
            progress.update(task_id, description="[bold green]Whisper model ready.")
            progress.remove_task(task_id)
            return True
        except ImportError:
            progress.update(task_id, description="[bold red]Whisper package not installed.")
            progress.remove_task(task_id)
            console.print("[red]Error: Whisper package not installed correctly. Please check requirements.txt.[/]")
            return False
        except Exception as e:
            progress.update(task_id, description="[bold red]Error preparing Whisper model.")
            progress.remove_task(task_id)
            console.print(f"[red]Error preparing Whisper model: {str(e)}[/]")
            return False

    def setup_env_file(self) -> bool:
        """Create or update .env file with user inputs."""
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
                "VERIFICATION_TOKEN": os.getenv("VERIFICATION_TOKEN", ""), # Added VERIFICATION_TOKEN
                "LLAMA_HOST": os.getenv("LLAMA_HOST", "http://localhost:11434"),
                "FLASK_SECRET_KEY": os.getenv("FLASK_SECRET_KEY", "") # Added FLASK_SECRET_KEY
            }

        # Show Zoom App setup instructions
        console.print(Panel(
            "[bold]To use this application, you need to create a Zoom OAuth App:[/]\n"
            "1. Go to https://marketplace.zoom.us/develop/create\n"
            "2. Select 'OAuth' app type\n"
            "3. Add redirect URL: [cyan]http://localhost:8000/oauth/callback[/]\n"
            "4. Add scopes: [cyan]meeting:read:meeting_transcript meeting:read:list_meetings "
            "meeting:read:poll meeting:read:token meeting:write:poll user:read:zak zoomapp:inmeeting[/]\n"
            "5. Copy your Client ID and Client Secret\n\n"
            "[bold]For Webhooks (Optional):[/]\n"
            "If you plan to use Zoom Webhooks, you will need a Secret Token and Verification Token from your app settings.",
            title="Zoom API Configuration"
        ))

        # Get user inputs with existing values as defaults
        client_id = Prompt.ask("Enter Zoom Client ID",
                                default=existing_values.get("CLIENT_ID", ""))

        client_secret = Prompt.ask("Enter Zoom Client Secret",
                                   default=existing_values.get("CLIENT_SECRET", ""))

        redirect_uri = Prompt.ask("Redirect URI",
                                  default=existing_values.get("REDIRECT_URI", "http://localhost:8000/oauth/callback"))

        secret_token = Prompt.ask("Enter Zoom Webhook Secret Token (Optional)",
                                  default=existing_values.get("SECRET_TOKEN", ""))

        verification_token = Prompt.ask("Enter Zoom Webhook Verification Token (Optional)",
                                        default=existing_values.get("VERIFICATION_TOKEN", ""))


        console.print("\n[bold]Other Configuration[/bold]")

        # Ollama host
        llama_host = Prompt.ask("Ollama Host",
                                default=existing_values.get("LLAMA_HOST", "http://localhost:11434"))

        # Flask Secret Key
        console.print(Panel(
            "[bold]Flask Secret Key:[/]\n"
            "This is used by Flask for session management and security. It should be a long, random, and persistent value.\n"
            "If you leave this blank, a new random key will be generated, but sessions will be lost if you restart the app.",
            title="Flask Configuration"
        ))
        flask_secret_key = Prompt.ask("Enter Flask Secret Key (Leave blank to auto-generate)",
                                      default=existing_values.get("FLASK_SECRET_KEY", ""))

        # Auto-generate Flask Secret Key if left blank
        if not flask_secret_key:
            flask_secret_key = secrets.token_hex(24)
            console.print("[yellow]Auto-generated Flask Secret Key.[/]")


        # Write to .env file
        try:
            with open(".env", "w") as f:
                f.write("# OAuth credentials (from your Zoom App)\n")
                f.write("# You need to register a Zoom App in the Zoom Developer Portal at https://marketplace.zoom.us/\n")
                f.write(f"CLIENT_ID={client_id}\n")
                f.write(f"CLIENT_SECRET={client_secret}\n")
                f.write("# Redirect URI (must match exactly in Zoom App settings)\n")
                f.write(f"REDIRECT_URI={redirect_uri}\n")
                f.write("# Webhook verification tokens (for future use)\n")
                f.write(f"SECRET_TOKEN={secret_token}\n")
                f.write(f"VERIFICATION_TOKEN={verification_token}\n")
                f.write("# Ollama host (LLaMA)\n")
                f.write(f"LLAMA_HOST={llama_host}\n")
                f.write("# Flask Secret Key for session management\n")
                f.write("# Generate a strong random key (e.g., using python -c \"import os; print(os.urandom(24).hex())\")\n")
                f.write(f"FLASK_SECRET_KEY={flask_secret_key}\n")


            # Verify the environment variables are set (at least the required ones)
            load_dotenv(override=True)
            if not os.getenv("CLIENT_ID") or not os.getenv("CLIENT_SECRET") or not os.getenv("FLASK_SECRET_KEY"):
                console.print("[red]Error: CLIENT_ID, CLIENT_SECRET, and FLASK_SECRET_KEY must be set in .env file[/]")
                return False

            console.print("[green]✓ .env file has been created/updated.[/]")
            return True
        except Exception as e:
            console.print(f"[red]Failed to write .env file: {str(e)}[/]")
            return False


    def run(self) -> bool:
        """Run the setup wizard."""
        console.print(Panel("[bold blue]Zoom Poll Automator Setup Wizard[/bold blue]", expand=False))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True # Remove tasks when completed
        ) as progress:

            # Check if dependencies are already installed
            task_deps_check = progress.add_task("[bold blue]Checking if dependencies are already installed...", total=None)
            if self.check_dependencies_installed():
                progress.update(task_deps_check, description="[bold green]Dependencies appear to be installed.")
                progress.remove_task(task_deps_check)
            else:
                progress.update(task_deps_check, description="[bold yellow]Dependencies not fully detected. Installing...")
                progress.remove_task(task_deps_check)
                if not self.install_dependencies(progress):
                    return False

            # Check FFmpeg
            if not self.check_ffmpeg(progress):
                 # FFmpeg is optional, continue but warn
                 pass

            # Check Ollama
            if not self.check_ollama(progress):
                 # Ollama is required for LLM features, but app might run without it for other functions
                 # Decide if this is a fatal error or just a warning based on app requirements
                 # For now, let's make it a warning and continue
                 console.print("[yellow]Warning: Ollama setup incomplete. LLM features may not work.[/]")


            # Download Whisper model
            if not self.download_whisper_model(progress):
                 # Whisper is likely required for transcription
                 console.print("[red]Error: Whisper model setup failed. Transcription may not work.[/]")
                 # Decide if this is fatal, for now, let's make it fatal
                 return False


        # Setup .env file (interactive, outside of progress bar)
        if not self.setup_env_file():
            return False

        console.print("\n[bold green]✓ Setup completed successfully![/bold green]")
        console.print("\nTo start the application:")
        console.print("1. Ensure your virtual environment is activated (it should be if you ran start.ps1 or start.sh).")
        console.print("2. Run the application:")
        console.print("   [bold cyan]python app.py[/bold cyan]")

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
        console.print(f"[bold red]An unhandled error occurred during setup: {str(e)}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
