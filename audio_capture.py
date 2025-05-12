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
import os
import time
import wave
import threading

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logging.warning("PyAudio not available. Using alternative audio capture method.")

try:
    import sounddevice as sd
    import soundfile as sf
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    logging.warning("SoundDevice not available. Using alternative audio capture method.")

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

def apply_noise_reduction(audio_data: np.ndarray, rate: int = 44100) -> np.ndarray:
    """Apply a simple noise reduction filter to the audio data"""
    try:
        # Simple noise reduction using median filtering
        noise_profile = np.median(np.abs(audio_data[:rate//2]))  # Use first 0.5s as noise profile
        # Apply soft thresholding with the noise profile
        denoised = np.sign(audio_data) * np.maximum(0, np.abs(audio_data) - noise_profile * 0.5)
        logger.info("Applied noise reduction")
        return denoised
    except Exception as e:
        logger.error(f"Error applying noise reduction: {str(e)}")
        return audio_data  # Return original data on error

def get_device_by_name(name: str) -> Optional[Union[AudioDevice, Dict[str, Any]]]:
    """Find a device by name (or partial match)."""
    devices = list_audio_devices()
    for device in devices:
        if name.lower() in device.name.lower():
            return device
    return None

def capture_audio(device, stop_event: threading.Event, duration_seconds: int = 30) -> str:
    """
    Capture audio from the specified device for the specified duration
    or until the stop event is set.
    
    Args:
        device: Audio device to use (index, name, or AudioDevice object)
        stop_event: Event to signal stopping the capture
        duration_seconds: Maximum duration in seconds
        
    Returns:
        Path to the captured audio file
    """
    try:
        # Create output directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Generate a unique filename
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_path = str(logs_dir / f"audio_{timestamp}.wav")
        
        # Get device info
        device_id = None
        channels = 2
        sample_rate = 44100
        
        if isinstance(device, AudioDevice):
            device_id = device.index
            channels = device.channels if device.channels <= 2 else 2
        elif isinstance(device, dict) and 'index' in device:
            device_id = device['index']
            channels = device.get('max_input_channels', 2)
            if channels > 2:
                channels = 2
        elif isinstance(device, (int, str)):
            device_id = device
        
        # Check which audio library to use
        if SOUNDDEVICE_AVAILABLE:
            logger.info(f"Capturing audio with SoundDevice for {duration_seconds}s")
            success = record_with_sounddevice(device_id, duration_seconds, sample_rate, channels, output_path)
        elif PYAUDIO_AVAILABLE:
            logger.info(f"Capturing audio with PyAudio for {duration_seconds}s")
            success = record_with_pyaudio(device_id, duration_seconds, sample_rate, channels, output_path)
        else:
            logger.warning("No audio libraries available. Creating silent audio file.")
            success = create_silent_audio(output_path, duration_seconds, sample_rate, channels)
        
        if success:
            logger.info(f"Audio captured to {output_path}")
            return output_path
        else:
            # If capture failed, create a silent file
            logger.warning("Audio capture failed. Creating silent audio file.")
            create_silent_audio(output_path, duration_seconds, sample_rate, channels)
            return output_path
    
    except Exception as e:
        logger.error(f"Error in capture_audio: {str(e)}", exc_info=True)
        # Create an empty file on error
        error_path = str(Path("logs") / f"error_audio_{time.strftime('%Y%m%d-%H%M%S')}.wav")
        create_silent_audio(error_path, 5, 16000, 1)
        return error_path

def record_with_pyaudio(device_id, duration_seconds, sample_rate, channels, output_path):
    """Record audio using PyAudio."""
    try:
        p = pyaudio.PyAudio()
        
        # Open audio stream
        stream = p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=device_id if isinstance(device_id, int) else None,
            frames_per_buffer=1024
        )
        
        # Record audio
        frames = []
        for i in range(0, int(sample_rate / 1024 * duration_seconds)):
            data = stream.read(1024, exception_on_overflow=False)
            frames.append(data)
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Write to output file
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(frames))
        
        # Process for transcription
        process_for_transcription(output_path)
        return True
    
    except Exception as e:
        logger.error(f"Error in record_with_pyaudio: {str(e)}", exc_info=True)
        return False

def record_with_sounddevice(device_id, duration_seconds, sample_rate, channels, output_path):
    """Record audio using SoundDevice."""
    try:
        # Record audio
        recording = sd.rec(
            int(duration_seconds * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            device=device_id if isinstance(device_id, int) else None
        )
        sd.wait()
        
        # Save to file
        sf.write(output_path, recording, sample_rate, 'PCM_16')
        
        # Process for transcription
        process_for_transcription(output_path)
        return True
    
    except Exception as e:
        logger.error(f"Error in record_with_sounddevice: {str(e)}", exc_info=True)
        return False

def create_silent_audio(output_path, duration_seconds, sample_rate, channels):
    """Create a silent audio file."""
    try:
        # Create silent audio
        silent_samples = np.zeros((int(duration_seconds * sample_rate), channels), dtype=np.int16)
        sf.write(output_path, silent_samples, sample_rate, 'PCM_16')
        logger.info(f"Created silent audio file: {output_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error creating silent audio: {str(e)}", exc_info=True)
        return False

def process_for_transcription(audio_path):
    """Process recorded audio to optimize for transcription."""
    try:
        # Load audio
        data, sr = sf.read(audio_path, dtype='float32')
        
        # Convert to mono if stereo
        if len(data.shape) > 1 and data.shape[1] > 1:
            data = data.mean(axis=1)
        
        # Resample to 16kHz for transcription
        if sr != 16000:
            data = librosa.resample(data, orig_sr=sr, target_sr=16000)
            sr = 16000
        
        # Apply noise reduction
        data = apply_noise_reduction(data, sr)
        
        # Normalize audio
        data = data / (np.max(np.abs(data)) + 1e-8) * 0.9
        
        # Save processed audio
        sf.write(audio_path, data, sr, 'PCM_16')
        logger.info(f"Processed audio for transcription: {audio_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error processing audio for transcription: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    # For testing
    devices = list_audio_devices()
    for device in devices:
        console.print(f"Found device: {device}")
    
    success = record_segment(5)  # 5 seconds with default device
    console.print(f"Recording {'successful' if success else 'failed'}")