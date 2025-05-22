#!/usr/bin/env python3
import click
import os
import sys
import subprocess
import time
import webbrowser
import threading
import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.table import Table
from rich import box
from dotenv import load_dotenv
import config

console = Console()

def check_ollama():
    """Check if Ollama is running and has required model"""
    try:
        response = requests.get(f"{config.OLLAMA_API}/api/tags", timeout=5)
        if not response.ok:
            return False, "Cannot connect to Ollama server"
        
        models = response.json().get("models", [])
        llama_available = any("llama3.2" in model.get("name", "") for model in models)
        if not llama_available:
            return False, "llama3.2 model not found"
        
        return True, "Ollama is running and llama3.2 model is available"
    except requests.exceptions.RequestException as e:
        return False, f"Error checking Ollama: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def start_ollama():
    """Start Ollama server"""
    try:
        if sys.platform == "win32":
            subprocess.Popen(["start", "cmd", "/k", "ollama", "serve"], shell=True)
        else:
            subprocess.Popen(["gnome-terminal", "--", "ollama", "serve"])
        time.sleep(5)  # Wait for server to start
        return True
    except Exception as e:
        console.print(f"[red]Failed to start Ollama: {str(e)}[/]")
        return False

def check_environment():
    """Check if all required environment variables and services are available"""
    missing = []
    if not os.getenv("CLIENT_ID"):
        missing.append("CLIENT_ID")
    if not os.getenv("CLIENT_SECRET"):
        missing.append("CLIENT_SECRET")
    
    if missing:
        console.print(f"[red]Missing required configuration: {', '.join(missing)}[/]")
        console.print("[yellow]Please run 'zoom-poll setup' first[/]")
        return False
    
    return True

@click.group()
def cli():
    """Zoom Poll Automator - Automatically generate and post polls to Zoom meetings"""
    pass

@cli.command()
def setup():
    """Initial setup of Zoom Poll Automator"""
    console.print(Panel.fit(
        "[bold blue]Zoom Poll Automator Setup[/]",
        border_style="blue",
        box=box.ROUNDED
    ))
    
    # Check Python version
    python_version = sys.version.split()[0]
    console.print(f"[blue]Python version: {python_version}[/]")
    
    # Create virtual environment
    if not os.path.exists("venv"):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Creating virtual environment...", total=None)
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            progress.update(task, completed=True)
    
    # Activate virtual environment and install requirements
    if sys.platform == "win32":
        activate_script = "venv\\Scripts\\activate.bat"
        pip_cmd = ["venv\\Scripts\\pip"]
    else:
        activate_script = "source venv/bin/activate"
        pip_cmd = ["venv/bin/pip"]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Installing requirements...", total=None)
        subprocess.run(pip_cmd + ["install", "--upgrade", "pip"], check=True)
        subprocess.run(pip_cmd + ["install", "-r", "requirements.txt"], check=True)
        progress.update(task, completed=True)
    
    # Check Ollama
    ollama_ok, ollama_msg = check_ollama()
    if not ollama_ok:
        console.print(f"[yellow]{ollama_msg}[/]")
        if click.confirm("Do you want to start Ollama now?"):
            if start_ollama():
                console.print("[green]Started Ollama server[/]")
            else:
                console.print("[red]Failed to start Ollama[/]")
    
    # Setup environment variables
    if not os.path.exists(".env"):
        console.print(Panel.fit(
            "[bold]Zoom OAuth Configuration[/]",
            border_style="yellow",
            box=box.ROUNDED
        ))
        console.print("1. Go to https://marketplace.zoom.us/develop/create")
        console.print("2. Create an OAuth app")
        console.print("3. Add redirect URL: http://localhost:8000/oauth/callback")
        console.print("4. Add required scopes")
        
        client_id = click.prompt("Enter your Zoom Client ID")
        client_secret = click.prompt("Enter your Zoom Client Secret")
        
        with open(".env", "w") as f:
            f.write(f"CLIENT_ID={client_id}\n")
            f.write(f"CLIENT_SECRET={client_secret}\n")
            f.write("REDIRECT_URI=http://localhost:8000/oauth/callback\n")
            f.write(f"SECRET_TOKEN={os.urandom(24).hex()}\n")
            f.write("LLAMA_HOST=http://localhost:11434\n")
        
        console.print("[green]Configuration saved[/]")
    
    console.print(Panel.fit(
        "[bold green]Setup completed![/]\nRun 'zoom-poll start' to begin",
        border_style="green",
        box=box.ROUNDED
    ))

@cli.command()
def start():
    """Start the Zoom Poll Automator"""
    if not check_environment():
        return
    
    ollama_ok, ollama_msg = check_ollama()
    if not ollama_ok:
        console.print(f"[yellow]{ollama_msg}[/]")
        if click.confirm("Do you want to start Ollama now?"):
            if start_ollama():
                console.print("[green]Started Ollama server[/]")
            else:
                console.print("[red]Failed to start Ollama[/]")
                return
    
    console.print(Panel.fit(
        "[bold green]Starting Zoom Poll Automator[/]",
        border_style="green",
        box=box.ROUNDED
    ))
    console.print("Access the web interface at: http://localhost:8000")
    
    # Start the Flask application
    if "--no-browser" not in sys.argv:
        try:
            threading.Thread(target=lambda: webbrowser.open("http://localhost:8000"), daemon=True).start()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not open browser automatically: {str(e)}[/]")
            console.print("[yellow]Please open http://localhost:8000 manually[/]")
    
    try:
        from app import app
        app.run(host="0.0.0.0", port=8000, debug=False)
    except Exception as e:
        console.print(f"[red]Error starting Flask application: {str(e)}[/]")
        return 1

@cli.command()
def status():
    """Check the status of Zoom Poll Automator"""
    console.print(Panel.fit(
        "[bold]Zoom Poll Automator Status[/]",
        border_style="blue",
        box=box.ROUNDED
    ))
    
    # Create status table
    table = Table(show_header=True, header_style="bold blue", box=box.ROUNDED)
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    # Check Python environment
    python_version = sys.version.split()[0]
    venv_status = "Active" if os.path.exists("venv") else "Not found"
    table.add_row("Python", "✓", f"Version {python_version}")
    table.add_row("Virtual Environment", "✓" if venv_status == "Active" else "✗", venv_status)
    
    # Check Ollama
    ollama_ok, ollama_msg = check_ollama()
    table.add_row("Ollama", "✓" if ollama_ok else "✗", ollama_msg)
    
    # Check configuration
    load_dotenv()
    config_status = "Found" if os.path.exists(".env") else "Not found"
    credentials_status = "Configured" if os.getenv("CLIENT_ID") and os.getenv("CLIENT_SECRET") else "Missing"
    table.add_row("Configuration File", "✓" if config_status == "Found" else "✗", config_status)
    table.add_row("Zoom Credentials", "✓" if credentials_status == "Configured" else "✗", credentials_status)
    
    console.print(table)

if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/]")
        sys.exit(1) 