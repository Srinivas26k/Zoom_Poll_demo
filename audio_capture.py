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
        # 1. Simple noise gate threshold (removes low-level noise)
        noise_threshold = 0.005  # Adjust as needed
        audio_data = np.where(np.abs(audio_data) < noise_threshold, 0, audio_data)
        
        # 2. Apply a simple low-pass filter to reduce high-frequency noise
        if len(audio_data) > 100:  # Ensure we have enough samples
            window_size = 5
            smoothed = np.zeros_like(audio_data)
            padded = np.pad(audio_data, ((window_size//2, window_size//2), (0, 0)), mode='edge')
            for i in range(len(audio_data)):
                smoothed[i] = np.mean(padded[i:i+window_size], axis=0)
            return smoothed
    except Exception as e:
        logger.warning(f"Noise reduction failed, using original audio: {str(e)}")
    
    return audio_data

def get_device_by_name(name: str) -> Optional[Union[AudioDevice, Dict[str, Any]]]:
    """Get device by name"""
    devices = list_audio_devices()
    for device in devices:
        if isinstance(device, AudioDevice) and device.name == name:
            return device
        elif isinstance(device, dict) and device.get('name') == name:
            return device
    return None

def record_audio(device, duration_seconds: int = 30, sample_rate: int = 44100) -> str:
    """Record audio using the specified device and return the path to the saved file"""
    channels = 2
    if isinstance(device, AudioDevice):
        device_id = device.device_id
        channels = device.channels
    elif isinstance(device, dict):
        device_id = device.get('id')
        channels = device.get('channels', 2)
    else:
        # Try to convert to string and use as a device name
        try:
            device_name = str(device)
            device_obj = get_device_by_name(device_name)
            if device_obj:
                return record_audio(device_obj, duration_seconds, sample_rate)
            else:
                logger.warning(f"Device specification '{device_name}' not found, using default")
                device_id = None
        except:
            device_id = None
    
    # Create output directory if it doesn't exist
    output_dir = "audio_recordings"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = int(time.time())
    output_path = os.path.join(output_dir, f"recording_{timestamp}.wav")
    
    # Try recording with PyAudio first
    if PYAUDIO_AVAILABLE:
        try:
            return record_with_pyaudio(device_id, duration_seconds, sample_rate, channels, output_path)
        except Exception as e:
            logger.error(f"PyAudio recording failed: {e}")
            # Fall back to sounddevice if PyAudio fails
    
    # Fall back to sounddevice
    if SOUNDDEVICE_AVAILABLE:
        try:
            return record_with_sounddevice(device_id, duration_seconds, sample_rate, channels, output_path)
        except Exception as e:
            logger.error(f"SoundDevice recording failed: {e}")
    
    # If all methods failed, create a dummy silent audio file as a fallback
    try:
        create_silent_audio(output_path, duration_seconds, sample_rate, channels)
        logger.warning("Created silent audio file as fallback")
        return output_path
    except Exception as e:
        logger.error(f"Failed to create silent audio: {e}")
        raise RuntimeError("All audio recording methods failed")

def record_with_pyaudio(device_id, duration_seconds, sample_rate, channels, output_path):
    """Record audio using PyAudio"""
    logger.info(f"Recording {duration_seconds}s @{sample_rate}Hz, {channels} channels")
    
    p = pyaudio.PyAudio()
    chunk = 1024
    format = pyaudio.paInt16
    
    stream = p.open(
        format=format,
        channels=channels,
        rate=sample_rate,
        input=True,
        input_device_index=device_id,
        frames_per_buffer=chunk
    )
    
    logger.info("Started recording...")
    frames = []
    
    for i in range(0, int(sample_rate / chunk * duration_seconds)):
        data = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)
    
    logger.info("Finished recording")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Convert frames to numpy array for noise reduction
    audio_np = np.frombuffer(b''.join(frames), dtype=np.int16).reshape(-1, channels) / 32768.0
    
    # Apply noise reduction
    cleaned_audio = apply_noise_reduction(audio_np, sample_rate)
    
    # Convert back to int16
    cleaned_frames = (cleaned_audio * 32768.0).astype(np.int16).tobytes()
    
    # Save to WAV file
    wf = wave.open(output_path, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(format))
    wf.setframerate(sample_rate)
    wf.writeframes(cleaned_frames)
    wf.close()
    
    return output_path

def record_with_sounddevice(device_id, duration_seconds, sample_rate, channels, output_path):
    """Record audio using sounddevice"""
    logger.info(f"Recording {duration_seconds}s @{sample_rate}Hz, {channels} channels (using sounddevice)")
    
    recording = sd.rec(
        int(duration_seconds * sample_rate),
        samplerate=sample_rate,
        channels=channels,
        device=device_id
    )
    
    sd.wait()  # Wait for recording to complete
    
    # Apply noise reduction
    cleaned_recording = apply_noise_reduction(recording, sample_rate)
    
    # Save to file
    sf.write(output_path, cleaned_recording, sample_rate)
    
    return output_path

def create_silent_audio(output_path, duration_seconds, sample_rate, channels):
    """Create a silent audio file as a fallback"""
    # Create silent audio data
    silent_data = np.zeros((int(duration_seconds * sample_rate), channels), dtype=np.int16)
    
    # Save to WAV file
    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 2 bytes for int16
        wf.setframerate(sample_rate)
        wf.writeframes(silent_data.tobytes())
    
    return output_path

if __name__ == "__main__":
    # For testing
    devices = list_audio_devices()
    for device in devices:
        console.print(f"Found device: {device}")
    
    success = record_segment(5)  # 5 seconds with default device
    console.print(f"Recording {'successful' if success else 'failed'}")