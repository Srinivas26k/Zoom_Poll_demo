import os
import time
import logging
import whisper
import torch
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhisperTranscriber:
    def __init__(self, model_name: str = "base"):
        """Initialize the Whisper transcriber with specified model."""
        self.model_name = model_name
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.temp_file_prefix = "zoom_audio_"
        logger.info(f"Using device: {self.device}")
        
    @lru_cache(maxsize=1)
    def load_model(self) -> None:
        """Load the Whisper model if not already loaded."""
        if self.model is None:
            try:
                start_time = time.time()
                logger.info(f"Loading Whisper model: {self.model_name}")
                self.model = whisper.load_model(self.model_name, device=self.device)
                load_time = time.time() - start_time
                logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
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
            start_time = time.time()
            logger.info(f"Transcribing audio file: {audio_path}")
            
            # Transcribe the audio
            result = self.model.transcribe(
                audio_path,
                language="en",
                fp16=False if self.device == "cpu" else True
            )
            
            transcription_time = time.time() - start_time
            logger.info(f"Transcription completed in {transcription_time:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            raise
    
    def get_temp_file_path(self, suffix: str = ".wav") -> str:
        """Get a unique temporary file path."""
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time())
        return str(Path(temp_dir) / f"{self.temp_file_prefix}{timestamp}{suffix}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.model is not None:
            logger.info("Cleaning up model resources")
            del self.model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("CUDA cache cleared")
            self.model = None
            logger.info("Model resources cleaned up")

# For backward compatibility
def get_temp_file_path() -> str:
    """Get a unique temporary file path (legacy function)."""
    return WhisperTranscriber().get_temp_file_path()

def transcribe_audio(audio_path: str) -> Dict[str, Any]:
    """
    Standalone function to transcribe audio using Whisper.
    This is a wrapper around WhisperTranscriber for backward compatibility.
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        Dict containing transcription results
    """
    transcriber = WhisperTranscriber()
    try:
        result = transcriber.transcribe_audio(audio_path)
        return result
    finally:
        transcriber.cleanup()
