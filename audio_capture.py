import sounddevice as sd
import soundfile as sf
import numpy as np
import librosa
import logging
from pathlib import Path
from typing import Optional, List, Dict, Union, Any
from rich.console import Console
from rich.logging import RichHandler
import os
import time
import wave
import threading
import pyaudiowpatch as pyaudio  # Using pyaudiowpatch for system audio capture

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("audio_capture")
console = Console()

class AudioDevice:
    def __init__(self, index: int, name: str, channels: int):
        self.index = index
        self.name = name
        self.channels = channels
    
    def __str__(self) -> str:
        return f"{self.name} (Channels: {self.channels})"

class AudioCapture:
    def __init__(self):
        self.default_samplerate = 44100
        self.default_channels = 2
        self.target_samplerate = 16000
        self.target_channels = 1
        self.pa = pyaudio.PyAudio()
    
    def list_audio_devices(self) -> List[AudioDevice]:
        """List all available audio input devices including system audio."""
        devices = []
        
        try:
            # List all devices including loopback devices
            for i in range(self.pa.get_device_count()):
                device_info = self.pa.get_device_info_by_index(i)
                
                # Include both regular input devices and loopback devices
                if device_info['maxInputChannels'] > 0 or 'hostapi' in device_info:
                    device = AudioDevice(
                        index=i,
                        name=device_info['name'],
                        channels=device_info['maxInputChannels']
                    )
                    devices.append(device)
                    logger.info(f"Found device: {device}")
            
            # Add virtual device for system audio capture
            devices.append(AudioDevice(
                index=-1,
                name="System Audio (All Participants)",
                channels=2
            ))
            
        except Exception as e:
            logger.error(f"Error listing audio devices: {str(e)}", exc_info=True)
        
        return devices

    def record_segment(
        self,
        duration: int,
        samplerate: int = 44100,
        channels: int = 2,
        output: str = "segment.wav",
        device: Optional[Union[str, int, Dict[str, Any]]] = None
    ) -> bool:
        """Record audio segment including system audio."""
        try:
            # Setup audio stream for system audio capture
            stream = self.pa.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=samplerate,
                input=True,
                input_device_index=self._get_device_index(device),
                frames_per_buffer=1024,
                stream_callback=None
            )
            
            logger.info(f"Recording {duration}s @{samplerate}Hz, {channels} channels")
            
            frames = []
            for _ in range(0, int(samplerate / 1024 * duration)):
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)
            
            # Stop and close stream
            stream.stop_stream()
            stream.close()
            
            # Convert to numpy array
            audio_data = np.frombuffer(b''.join(frames), dtype=np.float32)
            
            # Process audio for transcription
            if channels > 1:
                audio_data = audio_data.reshape(-1, channels)
                audio_data = audio_data.mean(axis=1)  # Convert to mono
            
            # Resample if needed
            if samplerate != self.target_samplerate:
                audio_data = librosa.resample(
                    audio_data,
                    orig_sr=samplerate,
                    target_sr=self.target_samplerate
                )
            
            # Normalize audio
            audio_data = librosa.util.normalize(audio_data)
            
            # Save processed audio
            sf.write(output, audio_data, self.target_samplerate, 'PCM_16')
            logger.info(f"Saved processed audio to {output}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during audio recording/processing: {str(e)}", exc_info=True)
            return False

    def _get_device_index(self, device_spec: Union[str, int, Dict[str, Any], None]) -> Optional[int]:
        """Get device index, handling system audio capture device."""
        if device_spec is None:
            return None
            
        if isinstance(device_spec, dict) and device_spec.get('name') == "System Audio (All Participants)":
            # Find the appropriate system audio capture device
            for i in range(self.pa.get_device_count()):
                device_info = self.pa.get_device_info_by_index(i)
                if 'hostapi' in device_info and device_info.get('isLoopbackDevice', False):
                    return i
            return None
            
        if isinstance(device_spec, (int, str)):
            return device_spec
            
        return None

    def __del__(self):
        """Cleanup PyAudio."""
        if hasattr(self, 'pa'):
            self.pa.terminate()

# Convenience functions
def list_audio_devices() -> List[AudioDevice]:
    """List available audio devices."""
    return AudioCapture().list_audio_devices()

def record_segment(
    duration: int,
    samplerate: int = 44100,
    channels: int = 2,
    output: str = "segment.wav",
    device: Optional[Union[str, int, Dict[str, Any]]] = None
) -> bool:
    """Record an audio segment."""
    return AudioCapture().record_segment(duration, samplerate, channels, output, device)