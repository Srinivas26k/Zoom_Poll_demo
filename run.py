import os
import time
# import shutil # Unused
import logging
import signal
import sys
import argparse
# from pathlib import Path # Unused
# from typing import Optional, Tuple, List # Unused
# from dotenv import load_dotenv # Unused, config.py handles .env loading
from rich.console import Console
from rich.panel import Panel
# from rich.progress import Progress, SpinnerColumn, TextColumn # Unused
from rich.logging import RichHandler

# from audio_capture import record_segment # Removed
# from transcribe_whisper import WhisperTranscriber # Removed
from meeting_recorder import MeetingRecorder # Added
# from poller import generate_poll_from_transcript # Unused directly
from poller import post_poll_to_zoom # Keep for callback
import config

# Create logs directory
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RichHandler(rich_tracebacks=True),
        logging.FileHandler("logs/run.log")
    ]
)
logger = logging.getLogger("zoom_poll_automator")
console = Console()

config.setup_config()

class ZoomPollAutomator:
    def __init__(self, test_mode: bool = False): # test_mode will be less effective now
        self.running = True
        # self.whisper = WhisperTranscriber() # Removed
        self.setup_signal_handlers()
        self.test_mode = test_mode # Will be re-evaluated, currently has minimal effect
        # self.retry_count = 0 # Removed
        # self.max_retry_count = 5 # Removed
        # self.base_delay = 5  # Removed
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
    
    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Received shutdown signal")
        self.running = False
    
    def check_environment(self) -> bool:
        """Check if all required environment variables and services are available."""
        try:
            # Check required environment variables
            required_vars = {
                "CLIENT_ID": "Zoom API Client ID",
                "CLIENT_SECRET": "Zoom API Client Secret",
                "MEETING_ID": "Zoom Meeting ID",
                "ZOOM_TOKEN": "Zoom Access Token"
            }
            
            missing = []
            for var, description in required_vars.items():
                if not os.getenv(var):
                    missing.append(f"{description} ({var})")
            
            if missing:
                logger.error(f"Missing required environment variables: {', '.join(missing)}")
                console.print("[yellow]Please run setup.bat first to configure the application.[/]")
                return False
            
            # Check Ollama connection
            try:
                import requests
                response = requests.get(f"{config.OLLAMA_API}/api/tags", timeout=5)
                response.raise_for_status()
                logger.info("Successfully connected to Ollama")
            except Exception as e:
                logger.error(f"Cannot connect to Ollama: {str(e)}")
                console.print("[red]Cannot connect to Ollama. Please make sure it's running.[/]")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking environment: {str(e)}")
            return False
    
    # cleanup_files method removed
    # calculate_backoff_delay method removed
    # process_cycle method removed
    
    def run(self):
        """Main run loop using MeetingRecorder."""
        if not self.check_environment():
            logger.error("Environment check failed. Exiting run.")
            return

        meeting_id_env = os.getenv("MEETING_ID")
        zoom_token_env = os.getenv("ZOOM_TOKEN")
        # segment_duration is handled by MeetingRecorder internally.

        console.print(Panel("[bold green]Zoom Poll Automator Started with MeetingRecorder[/bold green]\nPress Ctrl+C to stop", title="▶️ Live"))
        
        recorder = None
        try:
            # Using default device_name=None. Add CLI arg for device if needed.
            recorder = MeetingRecorder(device_name=None) 
            logger.info("MeetingRecorder initialized.")

            def post_new_poll_callback(poll_data):
                """Callback function to post new polls to Zoom."""
                logger.info(f"Callback triggered for new poll: {poll_data.get('title')}")
                try:
                    success = post_poll_to_zoom(
                        title=poll_data['title'],
                        question=poll_data['question'],
                        options=poll_data['options'],
                        meeting_id=meeting_id_env,
                        token=zoom_token_env
                    )
                    if success:
                        logger.info(f"Poll '{poll_data['title']}' posted to Zoom successfully via callback.")
                        console.print(f"[green]🚀 Poll '{poll_data['title']}' posted to Zoom.[/green]")
                    else:
                        logger.warning(f"Failed to post poll '{poll_data['title']}' to Zoom via callback.")
                        console.print(f"[yellow]⚠️ Failed to post poll '{poll_data['title']}' to Zoom.[/yellow]")
                except Exception as e:
                    logger.error(f"Error in poll posting callback for '{poll_data['title']}': {e}", exc_info=True)
                    console.print(f"[red]❌ Error posting poll '{poll_data['title']}': {e}[/]")

            recorder.on_poll_created = post_new_poll_callback
            logger.info("Poll creation callback assigned to MeetingRecorder.")

            if not recorder.start_recording():
                logger.error("Failed to start MeetingRecorder.")
                console.print("[red]❌ Failed to start MeetingRecorder. Exiting.[/red]")
                return
            
            logger.info("MeetingRecorder started successfully. Running until stop signal.")

            # Main loop: keep alive while MeetingRecorder works in threads
            while self.running:  # self.running is controlled by signal handlers
                time.sleep(1)
            logger.info("Loop terminated due to self.running becoming false (likely shutdown signal).")

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received, initiating graceful shutdown...")
            console.print("\n[yellow]KeyboardInterrupt received. Shutting down...[/yellow]")
            # self.running will be set to False by signal handler or already False
        except Exception as e:
            logger.error(f"Unexpected error in main run loop: {str(e)}", exc_info=True)
            console.print(f"\n[bold red]An unexpected error occurred: {str(e)}[/bold red]")
        finally:
            if recorder:
                logger.info("Stopping MeetingRecorder...")
                recorder.stop_recording()
                logger.info("MeetingRecorder stopped.")
                recorder.close()
                logger.info("MeetingRecorder resources closed.")
            # self.whisper.cleanup() # Removed as self.whisper is removed
            console.print("\n[bold red]Zoom Poll Automator stopped. Goodbye![/bold red]")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Zoom Poll Automator")
    parser.add_argument("--test", action="store_true", help="Run a single test cycle and exit")
    parser.add_argument("--duration", type=int, help="Recording duration in seconds")
    return parser.parse_args()

def main():
    """Entry point for the application."""
    try:
        args = parse_args()
        
        # Override environment variables if provided as arguments
        if args.duration:
            os.environ["SEGMENT_DURATION"] = str(args.duration)
            
        automator = ZoomPollAutomator(test_mode=args.test)
        automator.run()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        console.print(f"\n[bold red]Fatal error: {str(e)}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
