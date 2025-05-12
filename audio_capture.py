# audio_capture.py

import sounddevice as sd
import soundfile as sf
import numpy as np
import librosa
import logging
from pathlib import Path
from typing import Optional, List, Dict, Union, Any
from rich.console import Console
from rich.logging import RichHandler

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
    
    def list_audio_devices(self) -> List[AudioDevice]:
        """List all available audio input devices and return them as AudioDevice objects."""
        try:
            devices = sd.query_devices()
            input_devices = []
            
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:  # Only show input devices
                    device = AudioDevice(
                        index=i,
                        name=dev['name'],
                        channels=dev['max_input_channels']
                    )
                    input_devices.append(device)
                    logger.info(f"Found input device: {device}")
            
            if not input_devices:
                logger.warning("No input devices found")
            
            return input_devices
            
        except Exception as e:
            logger.error(f"Error listing audio devices: {str(e)}", exc_info=True)
            return []
    
    def find_device(self, device_spec: Union[str, int, Dict[str, Any], None]) -> Optional[int]:
        """Find audio device by name, index, or dictionary specification."""
        if device_spec is None:
            logger.info("Using default audio device")
            return None
            
        try:
            if isinstance(device_spec, dict):
                if 'index' in device_spec:
                    logger.info(f"Using device index {device_spec['index']}: {device_spec.get('name', 'Unknown')}")
                    return device_spec['index']
                elif 'name' in device_spec:
                    return self._find_device_by_name(device_spec['name'])
            elif isinstance(device_spec, str):
                return self._find_device_by_name(device_spec)
            elif isinstance(device_spec, int):
                logger.info(f"Using device index {device_spec}")
                return device_spec
                
            logger.warning(f"Device specification '{device_spec}' not found, using default")
            return None
            
        except Exception as e:
            logger.error(f"Error finding device: {str(e)}", exc_info=True)
            return None
    
    def _find_device_by_name(self, device_name: str) -> Optional[int]:
        """Find device index by name (supports partial matches)."""
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if device_name.lower() in dev['name'].lower() and dev['max_input_channels'] > 0:
                logger.info(f"Found device {i}: {dev['name']}")
                return i
        return None
    
    def record_segment(
        self,
        duration: int,
        samplerate: int = 44100,
        channels: int = 2,
        output: str = "segment.wav",
        device: Optional[Union[str, int, Dict[str, Any]]] = None
    ) -> bool:
        """
        Record audio segment and process it for transcription.
        
        Args:
            duration: Recording duration in seconds
            samplerate: Input sample rate (default: 44100 Hz)
            channels: Number of input channels (default: 2)
            output: Output file path
            device: Audio device specification
            
        Returns:
            bool: True if recording and processing was successful
        """
        temp_file = "temp_stereo.wav"
        device_index = self.find_device(device)
        
        try:
            # Record audio
            logger.info(f"Recording {duration}s @{samplerate}Hz, {channels} channels")
            audio = sd.rec(
                int(duration * samplerate),
                samplerate=samplerate,
                channels=channels,
                dtype="int16",
                device=device_index
            )
            sd.wait()
            
            # Save temporary stereo file
            sf.write(temp_file, audio, samplerate, subtype="PCM_16")
            logger.info("Saved temporary stereo file")
            
            # Process audio for transcription
            data, sr = sf.read(temp_file, dtype="float32")
            mono = data.mean(axis=1)  # Mix to mono
            mono16 = librosa.resample(mono, orig_sr=sr, target_sr=self.target_samplerate)
            
            # Normalize RMS
            rms = np.sqrt((mono16**2).mean())
            mono16 = mono16 * (0.1 / (rms + 1e-8))
            
            # Save final file
            sf.write(output, mono16, self.target_samplerate, subtype="PCM_16")
            logger.info(f"Saved processed audio to {output}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during audio recording/processing: {str(e)}", exc_info=True)
            return False
            
        finally:
            # Cleanup temporary file
            try:
                if Path(temp_file).exists():
                    Path(temp_file).unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary file: {str(e)}")

def list_audio_devices() -> List[AudioDevice]:
    """Convenience function to list audio devices."""
    return AudioCapture().list_audio_devices()

def record_segment(
    duration: int,
    samplerate: int = 44100,
    channels: int = 2,
    output: str = "segment.wav",
    device: Optional[Union[str, int, Dict[str, Any]]] = None
) -> bool:
    """Convenience function to record an audio segment."""
    return AudioCapture().record_segment(duration, samplerate, channels, output, device)

if __name__ == "__main__":
    # For testing
    devices = list_audio_devices()
    for device in devices:
        console.print(f"Found device: {device}")
    
    success = record_segment(5)  # 5 seconds with default device
    console.print(f"Recording {'successful' if success else 'failed'}")