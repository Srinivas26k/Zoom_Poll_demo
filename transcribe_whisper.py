import os
import time
import logging
import whisper
import torch
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache
from server_connection import RemoteModelProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhisperTranscriber:
    def __init__(self, model_name: str = "large", use_remote: bool = True):
        """Initialize the Whisper transcriber."""
        self.model_name = model_name
        self.use_remote = use_remote
        self.model = None
        self.remote_processor = None
        
        if use_remote:
            # Initialize remote processor with your server details
            self.remote_processor = RemoteModelProcessor(
                hostname="your-server.com",
                username="your-username",
                password="your-password"  # or key_filename="path/to/key"
            )
            self.remote_processor.connect()
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
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
        """Transcribe audio file using Whisper."""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        try:
            if self.use_remote:
                # Use remote Whisper Large model
                result = self.remote_processor.transcribe_with_whisper_large(audio_path)
                
                # Process with DeepSeek if needed
                if result.get("text"):
                    deepseek_result = self.remote_processor.process_with_deepseek(result["text"])
                    result["deepseek_analysis"] = deepseek_result
                
                return result
            else:
                # Use local model
                self.load_model()
                result = self.model.transcribe(
                    audio_path,
                    language="en",
                    fp16=False if self.device == "cpu" else True
                )
                return result
                
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            raise
    
    def get_temp_file_path(self, suffix: str = ".wav") -> str:
        """Get a unique temporary file path."""
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time())
        return str(Path(temp_dir) / f"zoom_audio_{timestamp}{suffix}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.use_remote and self.remote_processor:
            self.remote_processor.disconnect()
        elif self.model is not None:
            del self.model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            self.model = None

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
