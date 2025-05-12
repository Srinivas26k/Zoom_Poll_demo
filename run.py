import os
import time
import shutil
import logging
import signal
import sys
import argparse
from pathlib import Path
from typing import Optional, Tuple, List
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler

from audio_capture import record_segment
from transcribe_whisper import WhisperTranscriber
from poller import generate_poll_from_transcript, post_poll_to_zoom
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
    def __init__(self, test_mode: bool = False):
        self.running = True
        self.whisper = WhisperTranscriber()
        self.setup_signal_handlers()
        self.test_mode = test_mode
        self.retry_count = 0
        self.max_retry_count = 5
        self.base_delay = 5  # Base delay in seconds
        
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
    
    def cleanup_files(self):
        """Clean up temporary files."""
        try:
            for f in ("segment.wav", "temp_stereo.wav"):
                if os.path.exists(f):
                    os.remove(f)
                    logger.debug(f"Cleaned up {f}")
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")
    
    def calculate_backoff_delay(self) -> float:
        """Calculate exponential backoff delay based on retry count."""
        if self.retry_count == 0:
            return self.base_delay
        
        # Exponential backoff with jitter
        import random
        max_delay = min(60, self.base_delay * (2 ** self.retry_count))  # Cap at 60 seconds
        jitter = random.uniform(0.8, 1.2)  # Add 20% jitter
        delay = max_delay * jitter
        
        logger.info(f"Backoff delay: {delay:.2f} seconds (retry {self.retry_count}/{self.max_retry_count})")
        return delay
    
    def process_cycle(self, meeting_id: str, zoom_token: str, segment_duration: int) -> bool:
        """Process one cycle of recording, transcribing, and posting poll."""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                # 1) Record
                progress.add_task("🎙️ Recording audio...", total=None)
                record_success = record_segment(segment_duration, output="segment.wav")
                if not record_success:
                    logger.error("Failed to record audio")
                    return False

                # 2) Transcribe
                progress.add_task("🧠 Transcribing with Whisper...", total=None)
                transcript_result = self.whisper.transcribe_audio("segment.wav")
                transcript = transcript_result.get("text", "").strip()
                if not transcript:
                    logger.warning("No speech detected in audio")
                    return False

                console.print(Panel(transcript, title="📝 Transcript", width=80))

                # 3) Generate poll
                progress.add_task("🤖 Generating poll via LLaMA 3.2...", total=None)
                title, question, options = generate_poll_from_transcript(transcript)
                console.print(Panel(
                    f"[bold]{title}[/bold]\n\n{question}\n\n" + "\n".join(f"- {o}" for o in options),
                    title="❓ Poll Preview",
                    width=80
                ))

                # 4) Post poll
                progress.add_task("📤 Posting poll to Zoom...", total=None)
                success = post_poll_to_zoom(title, question, options, meeting_id, zoom_token)
                if success:
                    logger.info("Poll posted successfully")
                    console.print("[green]✅ Poll posted successfully![/]")
                    self.retry_count = 0  # Reset retry count on success
                    return True
                else:
                    logger.error("Failed to post poll to Zoom")
                    console.print("[red]❌ Failed to post poll to Zoom[/]")
                    self.retry_count += 1
                    return False
                
        except Exception as e:
            logger.error(f"Error in process cycle: {str(e)}", exc_info=True)
            self.retry_count += 1
            return False
    
    def run(self):
        """Main run loop."""
        if not self.check_environment():
            return

        meeting_id = os.getenv("MEETING_ID")
        zoom_token = os.getenv("ZOOM_TOKEN")
        segment_duration = int(os.getenv("SEGMENT_DURATION", "30"))

        cycle = 1
        console.print(Panel("[bold green]Zoom Poll Automator Started[/bold green]\nPress Ctrl+C to stop", title="▶️ Live"))

        try:
            while self.running:
                success = self.process_cycle(meeting_id, zoom_token, segment_duration)
                
                # Cleanup
                self.cleanup_files()
                
                if success:
                    cycle += 1
                    if self.test_mode:
                        logger.info("Test mode: Exiting after successful cycle")
                        console.print("\n[green]Test cycle completed successfully. Exiting.[/green]")
                        break
                    
                    console.print(f"\n[dim]Completed cycle {cycle}. Waiting 5s before next cycle...[/dim]")
                    time.sleep(5)
                else:
                    delay = self.calculate_backoff_delay()
                    console.print(f"\n[yellow]Waiting {delay:.1f}s before retrying...[/yellow]")
                    
                    if self.retry_count >= self.max_retry_count:
                        logger.error(f"Maximum retry count reached ({self.max_retry_count}). Stopping.")
                        console.print("\n[red]Maximum retry count reached. Stopping automation.[/red]")
                        break
                        
                    time.sleep(delay)

        except Exception as e:
            logger.error(f"Unexpected error in main loop: {str(e)}", exc_info=True)
            console.print(f"\n[bold red]Error: {str(e)}[/bold red]")
        finally:
            self.cleanup_files()
            self.whisper.cleanup()
            console.print("\n[bold red]Stopped. Goodbye![/bold red]")

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
