import os, time, shutil
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from audio_capture import record_segment
from transcribe_whisper import transcribe_segment
from poller import generate_poll_from_transcript, post_poll_to_zoom
import config

console = Console()
load_dotenv()  # reads .env

def check_environment():
    """Check if all required environment variables and services are available"""
    missing = []
    if not os.getenv("CLIENT_ID"):
        missing.append("CLIENT_ID")
    if not os.getenv("CLIENT_SECRET"):
        missing.append("CLIENT_SECRET")
    if not os.getenv("MEETING_ID"):
        missing.append("MEETING_ID")
    if not os.getenv("ZOOM_TOKEN"):
        missing.append("ZOOM_TOKEN")
    
    if missing:
        console.print(f"[red]Missing required environment variables: {', '.join(missing)}[/]")
        console.print("[yellow]Please run setup.bat first to configure the application.[/]")
        return False
    
    # Check Ollama connection
    try:
        import requests
        response = requests.get(f"{config.OLLAMA_API}/api/tags", timeout=5)
        if not response.ok:
            console.print("[red]Cannot connect to Ollama. Please make sure it's running.[/]")
            return False
    except Exception as e:
        console.print(f"[red]Error connecting to Ollama: {str(e)}[/]")
        return False
    
    return True

def main():
    if not check_environment():
        return

    MEETING_ID = os.getenv("MEETING_ID")
    ZOOM_TOKEN = os.getenv("ZOOM_TOKEN")
    SEGMENT_DURATION = int(os.getenv("SEGMENT_DURATION", "30"))

    cycle = 1
    console.print(Panel("[bold green]Zoom Poll Automator Started[/bold green]\nPress Ctrl+C to stop", title="▶️ Live"))

    try:
        while True:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                # 1) Record
                progress.add_task("🎙️ Recording audio...", total=None)
                record_success = record_segment(SEGMENT_DURATION, output="segment.wav")
                if not record_success:
                    console.print("[red]Failed to record audio. Skipping cycle.[/]")
                    time.sleep(5)
                    continue

                # 2) Transcribe
                progress.add_task("🧠 Transcribing with Whisper...", total=None)
                transcript = transcribe_segment("segment.wav")
                if not transcript.strip():
                    console.print("[yellow]No speech detected. Skipping poll generation.[/]")
                    time.sleep(5)
                    continue

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
                success = post_poll_to_zoom(title, question, options, MEETING_ID, ZOOM_TOKEN)
                if success:
                    console.print("[green]✅ Poll posted successfully![/]")
                else:
                    console.print("[red]❌ Failed to post poll to Zoom[/]")

            # Cleanup
            for f in ("segment.wav", "temp_stereo.wav"):
                if os.path.exists(f):
                    os.remove(f)

            cycle += 1
            console.print(f"\n[dim]Completed cycle {cycle}. Waiting 5s before next cycle...[/dim]")
            time.sleep(5)

    except KeyboardInterrupt:
        console.print("\n[bold red]Stopped by user. Goodbye![/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {str(e)}[/bold red]")
        console.print("[yellow]Please check your configuration and try again.[/]")

if __name__ == "__main__":
    main()
