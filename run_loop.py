# run_loop.py

import os
import time
from rich.console import Console
from meeting_recorder import MeetingRecorder # Added

console = Console()

def run_loop(device_name, should_stop):
    """
    Initializes MeetingRecorder, starts it, and keeps the loop alive
    until should_stop Event is set. Handles posting polls via a callback.
    
    Args:
        device_name: Audio device name to use for recording
        should_stop: threading.Event object to signal loop termination
    """
    console.log(f"[blue]▶️ Starting run_loop with device: {device_name}[/]")

    # Get configuration from environment
    zoom_token = os.getenv("ZOOM_TOKEN")
    meeting_id = os.getenv("MEETING_ID")
    # SEGMENT_DURATION is used by MeetingRecorder internally if configured, not directly here.

    if not zoom_token or not meeting_id:
        console.log("[red]❌ Missing ZOOM_TOKEN or MEETING_ID in environment. Poll posting will fail.[/]")
        return

    recorder = None
    try:
        console.log(f"Attempting to initialize MeetingRecorder with device: {device_name}")
        recorder = MeetingRecorder(device_name=device_name)
        console.log("[green]✅ MeetingRecorder initialized successfully.[/]")

        def post_new_poll_callback(poll_data):
            """Callback function to post new polls to Zoom."""
            from poller import post_poll_to_zoom # Local import
            
            console.log(f"💡 New poll generated: {poll_data.get('title')}")
            try:
                success = post_poll_to_zoom(
                    title=poll_data['title'],
                    question=poll_data['question'],
                    options=poll_data['options'],
                    meeting_id=meeting_id,
                    token=zoom_token
                )
                if success:
                    console.log(f"[green]🚀 Poll '{poll_data['title']}' posted to Zoom successfully.[/]")
                else:
                    console.log(f"[yellow]⚠️ Failed to post poll '{poll_data['title']}' to Zoom.[/]")
            except Exception as e:
                console.log(f"[red]❌ Error posting poll '{poll_data['title']}': {e}[/]")

        recorder.on_poll_created = post_new_poll_callback
        console.log("📝 Poll callback assigned to MeetingRecorder.")

        if not recorder.start_recording(): # Pass device_name for older start_recording if needed, or rely on __init__
            console.log("[red]❌ Failed to start MeetingRecorder. Exiting run_loop.[/]")
            return
        
        console.log("[green]🎤 MeetingRecorder started. Monitoring for stop signal...[/]")

        while not should_stop.is_set():
            # The main work is done by MeetingRecorder's threads.
            # This loop just keeps the main thread alive and checks the stop signal.
            time.sleep(1) 

    except ValueError as ve:
        console.log(f"[red]❌ ValueError during MeetingRecorder initialization: {ve}. Check audio device name and availability.[/]")
        return # Exit if MeetingRecorder cannot be initialized
    except Exception as e:
        console.log(f"[red]❌ An unexpected error occurred in run_loop: {e}[/]")
    finally:
        if recorder:
            console.log("[yellow]⏹️ Stopping MeetingRecorder...[/]")
            try:
                recorder.stop_recording()
                console.log("📼 MeetingRecorder recording stopped.")
                recorder.close()
                console.log("🚪 MeetingRecorder resources closed.")
            except Exception as e:
                console.log(f"[red]❌ Error during MeetingRecorder cleanup: {e}[/]")
        
        console.log("[green]✅ Automation loop terminated[/]")