# transcribe_whisper.py
import os
import whisper
from rich.console import Console
import soundfile as sf
import numpy as np

console = Console()

# Global model variable
model = None

def load_model():
    """Load the Whisper model if not already loaded"""
    global model
    if model is None:
        try:
            console.log("📥 Loading Whisper tiny.en model...")
            model = whisper.load_model("tiny.en")
            console.log("✅ Whisper model loaded successfully")
        except Exception as e:
            console.log(f"[red]❌ Failed to load Whisper model: {str(e)}[/]")
            raise
    return model

def ensure_audio_format(audio_path):
    """Ensure audio is in the correct format for Whisper"""
    try:
        # Read the audio file
        data, samplerate = sf.read(audio_path)
        
        # Convert to mono if stereo
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        # Resample to 16kHz if needed
        if samplerate != 16000:
            from scipy import signal
            samples = len(data)
            new_samples = int(samples * 16000 / samplerate)
            data = signal.resample(data, new_samples)
            samplerate = 16000
        
        # Save the processed audio
        processed_path = audio_path + ".processed.wav"
        sf.write(processed_path, data, samplerate)
        return processed_path
    except Exception as e:
        console.log(f"[red]❌ Audio processing error: {str(e)}[/]")
        return None

def transcribe_segment(audio_path):
    """
    Transcribe an audio segment using Whisper.
    
    Args:
        audio_path (str): Path to the audio file
        
    Returns:
        str: Transcribed text or empty string if failed
    """
    try:
        # Check if file exists
        if not os.path.exists(audio_path):
            console.log(f"[red]❌ Audio file not found: {audio_path}[/]")
            return ""
            
        # Get file size
        file_size = os.path.getsize(audio_path) / (1024 * 1024)  # Convert to MB
        console.log(f"📊 Audio file size: {file_size:.2f} MB")
        
        # Load model
        model = load_model()
        
        # Process audio
        processed_path = ensure_audio_format(audio_path)
        if not processed_path:
            return ""
            
        # Transcribe
        console.log(f"🧠 Transcribing {os.path.basename(audio_path)}...")
        result = model.transcribe(processed_path)
        
        # Cleanup processed file
        try:
            os.remove(processed_path)
        except:
            pass
            
        return result["text"].strip()
        
    except Exception as e:
        console.log(f"[red]❌ Transcription error: {str(e)}[/]")
        return ""

if __name__ == "__main__":
    # Test transcription
    test_file = "segment.wav"
    if os.path.exists(test_file):
        text = transcribe_segment(test_file)
        print(f"\nTranscription result: {text}")
    else:
        print(f"Test file {test_file} not found")