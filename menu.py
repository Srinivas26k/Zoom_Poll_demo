#!/usr/bin/env python3
# menu.py - Main menu system for Zoom Poll Automator

import os
import sys
import subprocess
import webbrowser
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from dotenv import load_dotenv

console = Console()

class MenuSystem:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.env_file = self.project_root / ".env"
        self.app_file = self.project_root / "app.py"
        self.setup_file = self.project_root / "setup.py"
        
        # Help URL
        self.help_url = "https://deepwiki.com/Srinivas26k/Zoom_Poll_demo/1-overview"
        
        # Determine OS and set appropriate paths
        if sys.platform == "win32":
            self.python_path = self.venv_path / "Scripts" / "python.exe"
            self.pip_path = self.venv_path / "Scripts" / "pip.exe"
        else:
            self.python_path = self.venv_path / "bin" / "python"
            self.pip_path = self.venv_path / "bin" / "pip"

    def display_header(self):
        """Display application header"""
        console.print(Panel(
            "[bold blue]Welcome to Zoom Poll Automator[/bold blue]\n"
            "Create accurate polls from meeting transcripts automatically",
            expand=False
        ))
    
    def display_menu(self):
        """Display the main menu options"""
        table = Table(show_header=False, box=None)
        table.add_column("Option", style="cyan")
        table.add_column("Description")
        
        table.add_row("1", "First Time Setup (Install & Configure)")
        table.add_row("2", "Run Automation")
        table.add_row("3", "Update Configuration")
        table.add_row("4", "Help Documentation")
        table.add_row("5", "Exit")
        
        console.print(table)
    
    def run_first_time_setup(self):
        """Run the full setup process for first-time users"""
        console.print("[bold]Running First Time Setup...[/bold]")
        
        # Check if venv exists, create if not
        if not self.venv_path.exists():
            console.print("Creating virtual environment...")
            try:
                subprocess.run([sys.executable, "-m", "venv", str(self.venv_path)], check=True)
                console.print("[green]✓ Virtual environment created[/green]")
            except subprocess.CalledProcessError as e:
                console.print(f"[red]Failed to create virtual environment: {str(e)}[/red]")
                return False

        # Activate the virtual environment
        if sys.platform == "win32":
            activate_script = self.venv_path / "Scripts" / "activate.bat"
            python_path = self.venv_path / "Scripts" / "python.exe"
        else:
            activate_script = self.venv_path / "bin" / "activate"
            python_path = self.venv_path / "bin" / "python"

        if not activate_script.exists():
            console.print("[red]Virtual environment activation script not found[/red]")
            return False

        try:
            # Install base dependencies needed for setup.py and menu.py itself
            console.print("\nInstalling essential dependencies for setup and menu...")
            subprocess.run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], check=True)
            # setup.py imports requests, rich, python-dotenv, secrets (secrets is standard)
            subprocess.run([str(python_path), "-m", "pip", "install", "rich", "python-dotenv", "requests"], check=True)
            console.print("[green]✓ Essential dependencies installed[/green]")

            # Run setup.py (which now handles all other dependencies)
            console.print("\nRunning main setup script (setup.py)...")
            subprocess.run([str(python_path), str(self.setup_file)], check=True)
            # The message "Setup completed successfully" will be printed by setup.py if it succeeds.
            # No need to print it again here explicitly unless setup.py's output isn't sufficient.

            # The line for installing all requirements is removed from here, as setup.py now handles it.
            # console.print("\nInstalling all dependencies...") # Removed
            # subprocess.run([str(python_path), "-m", "pip", "install", "-r", str(self.requirements_file)], check=True) # Removed
            # console.print("[green]✓ All dependencies installed[/green]") # Removed

            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Setup failed: {str(e)}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]An unexpected error occurred: {str(e)}[/red]")
            return False
    
    def run_automation(self):
        """Run the main automation application"""
        console.print("[bold]Starting Zoom Poll Automator...[/bold]")
        
        # Check if venv exists
        if not self.venv_path.exists():
            console.print("[yellow]Virtual environment not found. Please run First Time Setup first.[/yellow]")
            return False
        
        # Check if .env file exists with required configuration
        if not self.env_file.exists():
            console.print("[yellow]Configuration file not found. Please run First Time Setup first.[/yellow]")
            return False
        
        # Run the main application
        try:
            subprocess.run([str(self.python_path), str(self.app_file)], check=True)
            return True
        except subprocess.CalledProcessError:
            console.print("[red]Application exited with an error.[/red]")
            return False
    
    def update_configuration(self):
        """Update Zoom API keys and other configuration"""
        console.print("[bold]Updating Configuration...[/bold]")
        
        # Load the existing configuration
        if self.env_file.exists():
            load_dotenv(self.env_file)
        
        # Call only the env file setup part of setup.py
        try:
            # We'll create a simple script to call setup_env_file from setup.py
            update_script = """
from setup import SetupWizard
wizard = SetupWizard()
wizard.setup_env_file()
print("Configuration updated successfully.")
"""
            # Save to a temporary file
            temp_script = self.project_root / "_temp_update_config.py"
            with open(temp_script, "w") as f:
                f.write(update_script)
            
            # Run the temp script
            subprocess.run([str(self.python_path), str(temp_script)], check=True)
            
            # Delete the temporary file
            temp_script.unlink()
            
            console.print("[green]✓ Configuration updated successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Failed to update configuration: {str(e)}[/red]")
            return False
    
    def show_help(self):
        """Open help documentation in web browser"""
        console.print("[bold]Opening help documentation...[/bold]")
        try:
            webbrowser.open(self.help_url)
            console.print(f"[green]✓ Documentation opened in your browser: {self.help_url}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Failed to open documentation: {str(e)}[/red]")
            console.print(f"Please visit manually: {self.help_url}")
            return False
    
    def run(self):
        """Main menu loop"""
        try:
            while True:
                console.clear()
                self.display_header()
                self.display_menu()
                
                try:
                    choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "5"], default="2")
                    
                    if choice == "1":
                        success = self.run_first_time_setup()
                        if success:
                            console.print("[green]✓ First time setup completed successfully![/green]")
                        else:
                            console.print("[red]First time setup encountered some issues.[/red]")
                        Prompt.ask("\nPress Enter to continue")
                    elif choice == "2":
                        if not self.venv_path.exists() or not self.env_file.exists():
                            console.print("[yellow]Please run First Time Setup (Option 1) before starting the automation.[/yellow]")
                        else:
                            success = self.run_automation()
                            if not success:
                                console.print("[red]The automation encountered some issues. Please check the output above.[/red]")
                        Prompt.ask("\nPress Enter to continue")
                    elif choice == "3":
                        success = self.update_configuration()
                        if success:
                            console.print("[green]✓ Configuration updated successfully![/green]")
                        else:
                            console.print("[red]Failed to update configuration. Please try again.[/red]")
                        Prompt.ask("\nPress Enter to continue")
                    elif choice == "4":
                        success = self.show_help()
                        if not success:
                            console.print("[yellow]Could not open browser automatically. Please visit our documentation manually.[/yellow]")
                        Prompt.ask("\nPress Enter to continue")
                    elif choice == "5":
                        console.print("[bold green]Thank you for using Zoom Poll Automator![/bold green]")
                        return 0
                except Exception as e:
                    console.print(f"[red]An error occurred: {str(e)}[/red]")
                    Prompt.ask("\nPress Enter to continue")
        except KeyboardInterrupt:
            console.print("\n[yellow]Application closed by user.[/yellow]")
            return 0
        except Exception as e:
            console.print(f"[bold red]An unhandled error occurred: {str(e)}[/bold red]")
            return 1

if __name__ == "__main__":
    menu = MenuSystem()
    sys.exit(menu.run())