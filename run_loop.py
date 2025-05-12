# run_loop.py

import os, time
from rich.console import Console
from audio_capture import record_segment
from transcribe_whisper import WhisperTranscriber
from poller import generate_poll_from_transcript, post_poll_to_zoom

console = Console()

def run_loop(device, should_stop):
    """
    Forever: record → transcribe → generate + post poll → delete files
    Until should_stop Event is set.
    
    Args:
        device: Audio device name to use for recording
        should_stop: threading.Event object to signal loop termination
    """
    cycle = 0
    # Get configuration from environment
    zoom_token = os.getenv("ZOOM_TOKEN")
    meeting_id = os.getenv("MEETING_ID")
    duration = int(os.getenv("SEGMENT_DURATION", "30"))

    if not zoom_token or not meeting_id:
        console.log("[red]❌ Missing ZOOM_TOKEN or MEETING_ID in environment[/]")
        return

    whisper = WhisperTranscriber()

    while not should_stop.is_set():
        cycle += 1
        console.log(f"[blue]▶️  Cycle {cycle}[/]")
        try:
            # 1) Record
            record_success = record_segment(duration=duration, output="segment.wav", device=device)
            if not record_success:
                console.log("[yellow]⚠️ Recording failed—skipping cycle[/]")
                time.sleep(5)  # Wait a bit before next cycle
                continue

            # 2) Transcribe
            result = whisper.transcribe_audio("segment.wav")
            text = result.get("text", "") if isinstance(result, dict) else str(result)
            if not text.strip():
                console.log("[yellow]⚠️ Empty transcript—skipping poll[/]")
                time.sleep(5)  # Wait a bit before next cycle
                continue

            # 3) Generate poll
            title, question, options = generate_poll_from_transcript(text)

            # 4) Post poll
            post_poll_to_zoom(title, question, options, meeting_id, zoom_token)

            # 5) Cleanup
            for f in ("segment.wav", "temp_stereo.wav"):
                if os.path.exists(f):
                    os.remove(f)
            console.log("[green]🗑️  Cleaned up audio files[/]")

        except Exception as e:
            console.log(f"[red]❌ Error in run_loop:[/] {e}")
            time.sleep(5)  # Pause on error to avoid rapid error loops

        # Check if we should stop before continuing
        if should_stop.is_set():
            console.log("[yellow]⚠️ Stopping automation as requested[/]")
            break

        # small pause before next cycle
        time.sleep(1)
    
    console.log("[green]✅ Automation loop terminated[/]")