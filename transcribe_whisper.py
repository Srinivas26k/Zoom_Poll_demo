# transcribe_whisper.py
import whisper
import time
import os
from rich.console import Console

console = Console()
_model = None  # Lazy loading to avoid slow startup

def get_model():
    global _model
    if _model is None:
        console.log("📥 Loading Whisper tiny.en model...")
        try:
            _model = whisper.load_model("tiny.en")
            console.log("[green]✅ Whisper model loaded successfully[/]")
        except Exception as e:
            console.log(f"[red]❌ Error loading Whisper model:[/] {e}")
            raise
    return _model

def transcribe_segment(audio_path: str = "segment.wav") -> str:
    """
    Transcribe audio file using Whisper tiny.en model
    
    Args:
        audio_path (str): Path to the audio file to transcribe
        
    Returns:
        str: Transcribed text or empty string if transcription fails
    """
    console.log(f"🧠 Transcribing {audio_path}...")
    
    # Verify file exists
    if not os.path.exists(audio_path):
        console.log(f"[red]❌ Audio file not found:[/] {audio_path}")
        return ""
    
    # Check file size
    try:
        file_size = os.path.getsize(audio_path) / (1024 * 1024)  # Size in MB
        console.log(f"📊 Audio file size: {file_size:.2f} MB")
        
        if file_size < 0.001:
            console.log(f"[yellow]⚠️ Audio file is very small ({file_size:.2f} MB), may contain no audio[/]")
    except Exception as e:
        console.log(f"[yellow]⚠️ Could not check file size:[/] {e}")
    
    try:
        # Get the model (loads if not already loaded)
        model = get_model()
        
        # Measure transcription time
        start_time = time.time()
        
        # Perform transcription
        res = model.transcribe(audio_path)
        
        # Extract text
        text = res.get("text", "").strip()
        
        # Calculate processing time
        process_time = time.time() - start_time
        console.log(f"⏱️ Transcription took {process_time:.2f} seconds")
        
        # Log results
        if text:
            console.log(f"📝 Transcribed ({len(text)} chars): {text}")
        else:
            console.log("[yellow]⚠️ Transcription returned empty text[/]")
        
        return text
    except Exception as e:
        console.log(f"[red]❌ Transcription error:[/] {e}")
        return ""

# For testing
if __name__ == "__main__":
    result = transcribe_segment("segment.wav")
    print(f"Transcription result: {result}")