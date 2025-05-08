import os, time, shutil
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
<<<<<<< HEAD

from audio_capture    import record_segment
from transcribe_whisper import transcribe_segment
from extra.generate_poll    import generate_poll
from extra.post_poll        import post_poll
=======
from rich.progress import Progress, SpinnerColumn, TextColumn

from audio_capture import record_segment
from transcribe_whisper import transcribe_segment
from poller import generate_poll_from_transcript, post_poll_to_zoom
import config
>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)

console = Console()
load_dotenv()  # reads .env

<<<<<<< HEAD
MEETING_ID       = os.getenv("MEETING_ID")
ZOOM_TOKEN       = os.getenv("ZOOM_TOKEN")
SEGMENT_DURATION = int(os.getenv("SEGMENT_DURATION", "30"))

def main():
    if not (MEETING_ID and ZOOM_TOKEN):
        console.print("[red]Please set MEETING_ID and ZOOM_TOKEN in .env[/red]")
        return

=======
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

>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)
    cycle = 1
    console.print(Panel("[bold green]Zoom Poll Automator Started[/bold green]\nPress Ctrl+C to stop", title="▶️ Live"))

    try:
        while True:
<<<<<<< HEAD
            console.rule(f"Cycle {cycle}", style="cyan")

            # 1) Record
            console.print(f"🎙️ Recording [bold]{SEGMENT_DURATION}s[/bold]…")
            record_segment(SEGMENT_DURATION, out="segment.wav")
            console.print(":white_check_mark: [green]Audio captured → segment.wav[/green]")

            # 2) Transcribe
            console.print("🧠 Transcribing with Whisper…")
            transcript = transcribe_segment("segment.wav")
            console.print(Panel(transcript or "(no speech detected)", title="📝 Transcript", width=80))

            # 3) Generate poll
            console.print("🤖 Generating poll via LLaMA 3.2…")
            question, options = generate_poll(transcript)
            console.print(Panel(f"[bold]{question}[/bold]\n\n" + "\n".join(f"- {o}" for o in options),
                                title="❓ Poll Preview", width=80))

            # 4) Post poll
            console.print("📤 Posting poll to Zoom…")
            success, resp = post_poll(MEETING_ID, ZOOM_TOKEN, question, options)
            if success:
                console.print(Panel(str(resp), title="[green]✅ Poll Posted[/green]", width=80))
            else:
                console.print(Panel(str(resp), title="[red]❌ Poll Failed[/red]", width=80))

            # Cleanup
            for f in ("segment.wav",):
=======
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
>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)
                if os.path.exists(f):
                    os.remove(f)

            cycle += 1
<<<<<<< HEAD
            console.print("\n[dim]Waiting 5s before next cycle…[/dim]")
=======
            console.print(f"\n[dim]Completed cycle {cycle}. Waiting 5s before next cycle...[/dim]")
>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)
            time.sleep(5)

    except KeyboardInterrupt:
        console.print("\n[bold red]Stopped by user. Goodbye![/bold red]")
<<<<<<< HEAD
=======
    except Exception as e:
        console.print(f"\n[bold red]Error: {str(e)}[/bold red]")
        console.print("[yellow]Please check your configuration and try again.[/]")
>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)

if __name__ == "__main__":
    main()
