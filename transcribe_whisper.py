import os
import time
import logging
import whisper
import torch
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhisperTranscriber:
    def __init__(self, model_name: str = "base"):
        """Initialize the Whisper transcriber with specified model."""
        self.model_name = model_name
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
    def load_model(self) -> None:
        """Load the Whisper model if not already loaded."""
        if self.model is None:
            try:
                logger.info(f"Loading Whisper model: {self.model_name}")
                self.model = whisper.load_model(self.model_name, device=self.device)
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {str(e)}")
                raise
    
    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using Whisper.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dict containing transcription results
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        try:
            self.load_model()
            logger.info(f"Transcribing audio file: {audio_path}")
            
            # Transcribe the audio
            result = self.model.transcribe(
                audio_path,
                language="en",
                fp16=False if self.device == "cpu" else True
            )
            
            logger.info("Transcription completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            raise
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.model is not None:
            del self.model
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            self.model = None
            logger.info("Model resources cleaned up")

def get_temp_file_path() -> str:
    """Get a unique temporary file path."""
    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time())
    return str(Path(temp_dir) / f"zoom_audio_{timestamp}.wav")
