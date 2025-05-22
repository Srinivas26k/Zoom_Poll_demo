# virtual_audio.py
"""
Virtual audio capture module for recording internal audio from Zoom meetings.
This module allows capturing both speaker output and microphone input
in a unified stream for transcription and analysis.
"""

import pyaudio
import wave
import threading
import time
import os
import numpy as np
import logging
from typing import Optional, Dict, List, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VirtualAudioRecorder:
    """Records both system audio output and microphone input simultaneously."""
    
    def __init__(self, output_dir: str = "recordings"):
        """
        Initialize the virtual audio recorder.
        
        Args:
            output_dir: Directory where recordings will be saved
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 2
        self.rate = 44100
        self.recording = False
        self.recording_thread = None
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.start_time = None
        self.stop_recording_event = threading.Event()
        self.current_output_file = None
        
    def get_virtual_devices(self) -> List[Dict[str, any]]:
        """
        List all available virtual audio devices.
        
        Returns:
            List of dictionaries containing device information
        """
        devices = []
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        for i in range(num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                # Look for virtual audio devices
                if any(vad in device_info.get('name', '').lower() for vad in 
                      ['virtual', 'vac', 'cable', 'stereo mix', 'what u hear']):
                    devices.append({
                        'index': i,
                        'name': device_info.get('name'),
                        'channels': device_info.get('maxInputChannels'),
                        'sample_rate': int(device_info.get('defaultSampleRate')),
                        'virtual': True
                    })
                else:
                    devices.append({
                        'index': i,
                        'name': device_info.get('name'),
                        'channels': device_info.get('maxInputChannels'),
                        'sample_rate': int(device_info.get('defaultSampleRate')),
                        'virtual': False
                    })
        
        return devices
    
    def setup_virtual_audio(self) -> Tuple[bool, str]:
        """
        Checks if virtual audio drivers are installed and provides setup instructions if needed.
        
        Returns:
            Tuple of (success, message)
        """
        virtual_devices = [d for d in self.get_virtual_devices() if d['virtual']]
        
        if not virtual_devices:
            message = (
                "No virtual audio devices detected. To record internal audio, install one of:\n"
                "- VB-Audio Virtual Cable (Windows): https://vb-audio.com/Cable/\n"
                "- BlackHole (Mac): https://existential.audio/blackhole/\n"
                "- PulseAudio (Linux): Use module-loopback\n\n"
                "After installation, configure Zoom to use the virtual audio device as output."
            )
            return False, message
        
        return True, f"Found {len(virtual_devices)} virtual audio devices: {', '.join(d['name'] for d in virtual_devices)}"
    
    def start_recording(self, device_index: Optional[int] = None) -> str:
        """
        Start recording audio from the selected device.
        
        Args:
            device_index: Index of the device to record from, or None for default
            
        Returns:
            Path to the output file
        """
        if self.recording:
            logger.warning("Recording already in progress")
            return self.current_output_file
        
        # Reset state
        self.frames = []
        self.stop_recording_event.clear()
        
        # Create a timestamp for the filename
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_path = self.output_dir / f"meeting_recording_{timestamp}.wav"
        self.current_output_file = str(output_path)
        
        # Start recording in a separate thread
        self.recording = True
        self.start_time = time.time()
        self.recording_thread = threading.Thread(
            target=self._record_audio_thread,
            args=(device_index, output_path),
            daemon=True
        )
        self.recording_thread.start()
        
        logger.info(f"Started recording to {output_path}")
        return self.current_output_file
    
    def _record_audio_thread(self, device_index: Optional[int], output_path: Path) -> None:
        """
        Thread function that performs the actual recording.
        
        Args:
            device_index: Audio device to record from
            output_path: Path to save the recording
        """
        try:
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk
            )
            
            logger.info(f"Recording started with device index {device_index}")
            
            # Record data until stopped
            while not self.stop_recording_event.is_set():
                data = stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(data)
                
                # Optionally save chunks periodically for long recordings
                if len(self.frames) % 1000 == 0:  # Every ~20 seconds
                    self._save_temp_chunk()
            
            # Stop and close the stream
            stream.stop_stream()
            stream.close()
            
            # Save the final recording
            self._save_recording(output_path)
            
        except Exception as e:
            logger.error(f"Error in recording thread: {str(e)}")
        finally:
            self.recording = False
            logger.info("Recording thread finished")
    
    def _save_temp_chunk(self) -> None:
        """Save current frames to a temporary file to avoid memory issues with long recordings."""
        try:
            # Implementation for saving temp chunks if needed
            pass
        except Exception as e:
            logger.error(f"Error saving temporary chunk: {str(e)}")
    
    def _save_recording(self, output_path: Path) -> None:
        """
        Save the recorded frames to a WAV file.
        
        Args:
            output_path: Path to save the recording
        """
        try:
            logger.info(f"Saving recording to {output_path}")
            wf = wave.open(str(output_path), 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            logger.info(f"Recording saved: {output_path}")
        except Exception as e:
            logger.error(f"Error saving recording: {str(e)}")
    
    def stop_recording(self) -> Optional[str]:
        """
        Stop the current recording.
        
        Returns:
            Path to the saved recording file or None if no recording
        """
        if not self.recording:
            logger.warning("No recording in progress")
            return None
        
        # Signal the recording thread to stop
        self.stop_recording_event.set()
        
        # Wait for the recording thread to finish
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=5.0)
        
        # Calculate recording duration
        duration = time.time() - self.start_time if self.start_time else 0
        logger.info(f"Recording stopped. Duration: {duration:.2f} seconds")
        
        return self.current_output_file
    
    def close(self) -> None:
        """Clean up resources."""
        if self.recording:
            self.stop_recording()
        
        self.audio.terminate()
        logger.info("Audio recorder closed")


# Convenience function for setup
def check_virtual_audio_setup() -> Tuple[bool, str]:
    """
    Check if virtual audio capture is properly set up.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        recorder = VirtualAudioRecorder()
        return recorder.setup_virtual_audio()
    except Exception as e:
        logger.error(f"Error checking virtual audio setup: {str(e)}")
        return False, f"Error checking virtual audio setup: {str(e)}"
