# meeting_recorder.py
"""
Meeting recorder module for capturing, transcribing, and analyzing Zoom meetings.
Combines audio recording, real-time transcription, note generation, and poll creation.
"""

import os
import time
import threading
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable, Tuple
from datetime import datetime
import sounddevice as sd
import numpy as np
import wave
import queue

from virtual_audio import VirtualAudioRecorder
from transcribe_whisper import WhisperTranscriber
from poll_prompt import generate_poll
from rich.console import Console

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

class MeetingRecorder:
    """Main class for recording and analyzing Zoom meetings."""
    
    def __init__(self, device_name=None, audio_source='all'):
        """
        Initialize the meeting recorder.
        
        Args:
            device_name: Name of the audio device to record from, or None for default
            audio_source: Audio source ('host' or 'all')
        """
        self.device_name = device_name
        self.audio_source = audio_source
        self.is_recording = False
        self.is_paused = False
        self.start_time = None
        self.transcript = []
        self.transcript_lock = threading.Lock()
        self.audio_queue = queue.Queue()
        self.recording_thread = None
        self.processing_thread = None
        
        # Initialize audio device
        self.device_index = self._get_device_index(device_name)
        if self.device_index is None:
            raise ValueError(f"Audio device '{device_name}' not found")
        
        # Create output directory if it doesn't exist
        self.output_dir = "meetings"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Generate meeting ID
        self.meeting_id = f"Meeting-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Initialize poll generation
        self.generated_polls = []
        
        # Components
        self.audio_recorder = VirtualAudioRecorder(output_dir=str(self.output_dir / "audio"))
        self.transcriber = WhisperTranscriber(model_name="tiny.en")  # Use tiny.en for speed
        
        # State
        self.recording = False
        self.transcribing = False
        self.recording_file = None
        self.transcript_file = None
        self.notes_file = None
        self.full_transcript = ""
        self.transcript_segments = []
        self.summary_notes = []
        self.auto_polls = []
        
        # Threading
        self.stop_event = threading.Event()
        self.transcription_thread = None
        self.analysis_thread = None
        
        # Callbacks
        self.on_transcript_update = None
        self.on_note_generated = None
        self.on_poll_created = None
        
    def _get_device_index(self, device_name):
        """Get the device index by name"""
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device_name and device_name.lower() in device['name'].lower():
                return i
        return None
        
    def set_audio_source(self, audio_source):
        """Update the audio source (host-only or all participants)"""
        if audio_source not in ['host', 'all']:
            raise ValueError("Invalid audio source. Must be 'host' or 'all'")
        self.audio_source = audio_source
        logger.info(f"Audio source set to: {audio_source}")
        
    def start(self):
        """Start recording"""
        if self.is_recording:
            logger.warning("Recording already in progress")
            return False
            
        self.is_recording = True
        self.is_paused = False
        self.start_time = datetime.now()
        
        # Start recording thread
        self.recording_thread = threading.Thread(target=self._record_audio)
        self.recording_thread.start()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._process_audio)
        self.processing_thread.start()
        
        logger.info(f"Recording started with device: {self.device_name}")
        return True
        
    def stop(self):
        """Stop recording"""
        if not self.is_recording:
            logger.warning("No recording in progress")
            return False
            
        self.is_recording = False
        self.is_paused = False
        
        # Wait for threads to finish
        if self.recording_thread:
            self.recording_thread.join()
        if self.processing_thread:
            self.processing_thread.join()
            
        # Save final transcript
        self._save_transcript()
        
        logger.info("Recording stopped")
        return True
        
    def toggle_pause(self):
        """Toggle pause/resume recording"""
        if not self.is_recording:
            return False
            
        self.is_paused = not self.is_paused
        status = "paused" if self.is_paused else "resumed"
        logger.info(f"Recording {status}")
        return self.is_paused
        
    def _record_audio(self):
        """Record audio in a separate thread"""
        try:
            with sd.InputStream(device=self.device_index,
                              channels=1,
                              samplerate=16000,
                              dtype=np.int16) as stream:
                while self.is_recording:
                    if not self.is_paused:
                        audio_data, _ = stream.read(1024)
                        self.audio_queue.put(audio_data)
                    else:
                        time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error recording audio: {str(e)}")
            self.is_recording = False
            
    def _process_audio(self):
        """Process recorded audio in a separate thread"""
        try:
            while self.is_recording or not self.audio_queue.empty():
                if not self.is_paused:
                    try:
                        audio_data = self.audio_queue.get(timeout=1)
                        # Process audio data and generate transcript
                        transcript_entry = self._generate_transcript(audio_data)
                        if transcript_entry:
                            with self.transcript_lock:
                                self.transcript.append(transcript_entry)
                    except queue.Empty:
                        continue
                else:
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            
    def _generate_transcript(self, audio_data):
        """Generate transcript from audio data"""
        # TODO: Implement actual speech-to-text processing
        # For now, return a dummy transcript entry
        return {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'speaker': 'Host' if self.audio_source == 'host' else 'Unknown',
            'text': 'Sample transcript entry'
        }
        
    def _save_transcript(self):
        """Save transcript to file"""
        try:
            transcript_file = os.path.join(self.output_dir, f"{self.meeting_id}_transcript.json")
            with open(transcript_file, 'w') as f:
                json.dump(self.transcript, f, indent=2)
            logger.info(f"Transcript saved to {transcript_file}")
        except Exception as e:
            logger.error(f"Error saving transcript: {str(e)}")
            
    def get_transcript(self):
        """Get the complete transcript"""
        with self.transcript_lock:
            return self.transcript.copy()
            
    def get_latest_transcript(self):
        """Get the latest transcript entries"""
        with self.transcript_lock:
            # Return the last 10 entries or all if less than 10
            return self.transcript[-10:] if len(self.transcript) > 10 else self.transcript.copy()
            
    def get_generated_polls(self):
        """Get the generated polls"""
        return self.generated_polls
    
    def create_meeting_folder(self) -> Path:
        """
        Create a folder for the current meeting with timestamp.
        
        Returns:
            Path to the meeting folder
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.meeting_id = f"meeting_{timestamp}"
        meeting_dir = self.output_dir / self.meeting_id
        meeting_dir.mkdir(exist_ok=True, parents=True)
        return meeting_dir
    
    def start_recording(self, device_index: Optional[int] = None) -> bool:
        """
        Start recording and analyzing a meeting.
        
        Args:
            device_index: Audio device index to record from, or None for default
            
        Returns:
            True if recording started successfully, False otherwise
        """
        if self.recording:
            logger.warning("Recording already in progress")
            return False
        
        try:
            # Create meeting directory
            meeting_dir = self.create_meeting_folder()
            
            # Reset state
            self.full_transcript = ""
            self.transcript_segments = []
            self.summary_notes = []
            self.auto_polls = []
            self.stop_event.clear()
            
            # Start audio recording
            self.recording_file = self.audio_recorder.start_recording(device_index)
            
            # Initialize output files
            self.transcript_file = str(meeting_dir / "transcript.txt")
            self.notes_file = str(meeting_dir / "notes.json")
            
            # Start processing threads
            self.recording = True
            self.transcribing = True
            
            # Start transcription in a separate thread
            self.transcription_thread = threading.Thread(
                target=self._transcription_thread,
                daemon=True
            )
            self.transcription_thread.start()
            
            # Start analysis thread
            self.analysis_thread = threading.Thread(
                target=self._analysis_thread,
                daemon=True
            )
            self.analysis_thread.start()
            
            logger.info(f"Started recording meeting {self.meeting_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting meeting recording: {str(e)}")
            self.stop_recording()
            return False
    
    def stop_recording(self) -> Dict[str, Any]:
        """
        Stop recording and finish processing.
        
        Returns:
            Dict with paths to generated files
        """
        if not self.recording:
            logger.warning("No recording in progress")
            return {}
        
        try:
            # Signal threads to stop
            self.stop_event.set()
            
            # Stop audio recording
            self.audio_recorder.stop_recording()
            
            # Wait for processing to complete (with timeout)
            if self.transcription_thread and self.transcription_thread.is_alive():
                self.transcription_thread.join(timeout=10.0)
            
            if self.analysis_thread and self.analysis_thread.is_alive():
                self.analysis_thread.join(timeout=10.0)
            
            # Finalize transcription
            self._finalize_transcript()
            
            # Generate final notes and summary
            self._generate_final_summary()
            
            # Update state
            self.recording = False
            self.transcribing = False
            
            logger.info(f"Finished recording meeting {self.meeting_id}")
            
            return {
                "meeting_id": self.meeting_id,
                "recording": self.recording_file,
                "transcript": self.transcript_file,
                "notes": self.notes_file
            }
            
        except Exception as e:
            logger.error(f"Error stopping meeting recording: {str(e)}")
            return {}
        finally:
            # Reset state even if there was an error
            self.recording = False
            self.transcribing = False
    
    def _transcription_thread(self) -> None:
        """Thread that handles real-time transcription of the meeting audio."""
        try:
            # Load the model first
            self.transcriber.load_model()
            
            segment_interval = 30  # seconds
            segment_duration = 0
            last_processing_time = time.time()
            current_audio_chunk = self.audio_recorder.current_output_file
            
            logger.info("Transcription thread started")
            
            while not self.stop_event.is_set() and self.recording:
                current_time = time.time()
                segment_duration = current_time - last_processing_time
                
                # Process a segment every 30 seconds or when recording stops
                if segment_duration >= segment_interval:
                    # Create a copy of the current audio chunk for processing
                    temp_audio_path = f"{current_audio_chunk}.temp.wav"
                    
                    try:
                        # Process this segment
                        result = self.transcriber.transcribe_audio(temp_audio_path)
                        
                        if result and "text" in result:
                            transcript_text = result["text"].strip()
                            if transcript_text:
                                # Add to full transcript
                                if self.full_transcript:
                                    self.full_transcript += "\n\n" + transcript_text
                                else:
                                    self.full_transcript = transcript_text
                                
                                # Add segment with timestamp
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                segment = {
                                    "timestamp": timestamp,
                                    "text": transcript_text
                                }
                                self.transcript_segments.append(segment)
                                
                                # Save transcript
                                self._save_transcript()
                                
                                # Notify listeners
                                if self.on_transcript_update:
                                    self.on_transcript_update(segment, self.full_transcript)
                    
                    except Exception as e:
                        logger.error(f"Error processing audio segment: {str(e)}")
                    
                    finally:
                        # Clean up temporary file
                        if os.path.exists(temp_audio_path):
                            os.remove(temp_audio_path)
                        
                        last_processing_time = current_time
                
                # Sleep to avoid busy waiting
                time.sleep(1)
            
            # Process the final segment
            if self.recording_file and os.path.exists(self.recording_file):
                try:
                    final_result = self.transcriber.transcribe_audio(self.recording_file)
                    if final_result and "text" in final_result:
                        self.full_transcript = final_result["text"].strip()
                        # Save final transcript
                        self._save_transcript()
                except Exception as e:
                    logger.error(f"Error processing final transcript: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error in transcription thread: {str(e)}")
        finally:
            logger.info("Transcription thread finished")
    
    def _analysis_thread(self) -> None:
        """Thread that generates notes and polls based on transcript segments."""
        try:
            logger.info("Analysis thread started")
            
            poll_interval = 300  # 5 minutes
            note_interval = 120  # 2 minutes
            last_poll_time = time.time()
            last_note_time = time.time()
            
            while not self.stop_event.is_set() and self.recording:
                current_time = time.time()
                
                # Generate polls periodically
                if current_time - last_poll_time >= poll_interval:
                    try:
                        self._generate_poll()
                        last_poll_time = current_time
                    except Exception as e:
                        logger.error(f"Error generating poll: {str(e)}")
                
                # Generate notes periodically
                if current_time - last_note_time >= note_interval:
                    try:
                        self._generate_notes()
                        last_note_time = current_time
                    except Exception as e:
                        logger.error(f"Error generating notes: {str(e)}")
                
                # Sleep to avoid busy waiting
                time.sleep(5)
            
        except Exception as e:
            logger.error(f"Error in analysis thread: {str(e)}")
        finally:
            logger.info("Analysis thread finished")
    
    def _generate_notes(self) -> None:
        """Generate meeting notes based on transcript segments."""
        if not self.full_transcript or len(self.full_transcript) < 50:
            logger.debug("Not enough transcript content for notes generation")
            return
        
        try:
            # This is a placeholder; in a real implementation, 
            # we would call an LLM to generate meeting notes
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Simple note generation for demo purposes
            words = self.full_transcript.split()
            recent_words = words[-100:] if len(words) > 100 else words
            note_text = " ".join(recent_words)
            
            note = {
                "timestamp": timestamp,
                "content": f"Discussion about: {note_text[:50]}..."
            }
            
            self.summary_notes.append(note)
            
            # Save notes to file
            self._save_notes()
            
            # Notify listeners
            if self.on_note_generated:
                self.on_note_generated(note, self.summary_notes)
            
            logger.info(f"Generated meeting note at {timestamp}")
        except Exception as e:
            logger.error(f"Error generating meeting notes: {str(e)}")
    
    def _generate_poll(self) -> None:
        """Generate a poll based on the transcript content."""
        if not self.full_transcript or len(self.full_transcript) < 100:
            logger.debug("Not enough transcript content for poll generation")
            return
        
        try:
            # Call poll generation function from poll_prompt.py
            title, question, options = generate_poll(self.full_transcript)
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            poll = {
                "timestamp": timestamp,
                "title": title,
                "question": question,
                "options": options
            }
            
            self.auto_polls.append(poll)
            
            # Notify listeners
            if self.on_poll_created:
                self.on_poll_created(poll)
            
            logger.info(f"Generated poll: {title}")
        except Exception as e:
            logger.error(f"Error generating poll: {str(e)}")
    
    def _save_notes(self) -> None:
        """Save meeting notes to file."""
        if not self.notes_file:
            return
        
        try:
            meeting_data = {
                "meeting_id": self.meeting_id,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "notes": self.summary_notes,
                "polls": self.auto_polls
            }
            
            with open(self.notes_file, 'w', encoding='utf-8') as f:
                json.dump(meeting_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved meeting notes to {self.notes_file}")
        except Exception as e:
            logger.error(f"Error saving meeting notes: {str(e)}")
    
    def _finalize_transcript(self) -> None:
        """Finalize the transcript after recording is complete."""
        if not self.transcript_file or not self.full_transcript:
            return
        
        try:
            # Final save of the transcript
            with open(self.transcript_file, 'w', encoding='utf-8') as f:
                f.write(f"Meeting Transcript: {self.meeting_id}\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                f.write(self.full_transcript)
            
            logger.info(f"Finalized transcript at {self.transcript_file}")
        except Exception as e:
            logger.error(f"Error finalizing transcript: {str(e)}")
    
    def _generate_final_summary(self) -> None:
        """Generate final meeting summary and notes."""
        if not self.full_transcript or not self.notes_file:
            return
        
        try:
            # In a real implementation, this would call an LLM to generate a comprehensive summary
            
            # For demo purposes, create a simple summary
            word_count = len(self.full_transcript.split())
            duration_minutes = len(self.transcript_segments) * 30 // 60
            
            summary = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "content": f"Meeting ended. Duration: approximately {duration_minutes} minutes. "
                           f"Transcript contains {word_count} words."
            }
            
            self.summary_notes.append(summary)
            
            # Save final notes
            self._save_notes()
            
            logger.info("Generated final meeting summary")
        except Exception as e:
            logger.error(f"Error generating final summary: {str(e)}")
            
    def close(self) -> None:
        """Clean up resources."""
        try:
            if self.recording:
                self.stop_recording()
            
            self.audio_recorder.close()
            self.transcriber.cleanup()
            
            logger.info("Meeting recorder closed")
        except Exception as e:
            logger.error(f"Error closing meeting recorder: {str(e)}")
    
    def get_recording_duration(self) -> float:
        """
        Get the duration of the current recording in seconds.
        
        Returns:
            Duration in seconds (float)
        """
        if not self.recording or not hasattr(self.audio_recorder, 'start_time'):
            return 0.0
            
        if self.audio_recorder.start_time is None:
            return 0.0
            
        return time.time() - self.audio_recorder.start_time

    def get_recommended_devices(self, audio_source='all'):
        """
        Get recommended input devices based on the selected audio source.
        
        Args:
            audio_source: 'host' for host-only recording or 'all' for complete meeting
            
        Returns:
            dict: {
                'recommended': str,  # Best recommended device
                'alternatives': list,  # Alternative devices
                'all_devices': list,  # All available devices
                'explanation': str  # Explanation for the recommendation
            }
        """
        try:
            devices = sd.query_devices()
            input_devices = []
            
            # Filter for input devices
            for device in devices:
                if device['max_input_channels'] > 0:  # This is an input device
                    input_devices.append({
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'is_virtual': 'virtual' in device['name'].lower() or 'mix' in device['name'].lower(),
                        'is_microphone': 'mic' in device['name'].lower() or 'microphone' in device['name'].lower(),
                        'is_array': 'array' in device['name'].lower(),
                        'is_external': not any(x in device['name'].lower() for x in ['realtek', 'built-in', 'internal'])
                    })
            
            if audio_source == 'host':
                # For host-only recording, prioritize:
                # 1. External microphones
                # 2. Microphone arrays
                # 3. Other input devices
                recommended = None
                alternatives = []
                
                # First try to find an external microphone
                external_mics = [d for d in input_devices if d['is_external'] and d['is_microphone']]
                if external_mics:
                    recommended = external_mics[0]['name']
                    alternatives = [d['name'] for d in external_mics[1:]]
                
                # If no external mic, try microphone array
                if not recommended:
                    mic_arrays = [d for d in input_devices if d['is_array']]
                    if mic_arrays:
                        recommended = mic_arrays[0]['name']
                        alternatives = [d['name'] for d in mic_arrays[1:]]
                
                # If still no recommendation, use any microphone
                if not recommended:
                    mics = [d for d in input_devices if d['is_microphone']]
                    if mics:
                        recommended = mics[0]['name']
                        alternatives = [d['name'] for d in mics[1:]]
                
                explanation = "For host-only recording, we recommend using a dedicated microphone for the best voice quality."
                
            else:  # audio_source == 'all'
                # For complete meeting recording, prioritize:
                # 1. Virtual audio devices (Stereo Mix, etc.)
                # 2. System audio capture devices
                # 3. Microphones as fallback
                recommended = None
                alternatives = []
                
                # First try to find a virtual audio device
                virtual_devices = [d for d in input_devices if d['is_virtual']]
                if virtual_devices:
                    recommended = virtual_devices[0]['name']
                    alternatives = [d['name'] for d in virtual_devices[1:]]
                
                # If no virtual device, try system audio capture
                if not recommended:
                    system_devices = [d for d in input_devices if 'system' in d['name'].lower() or 'mix' in d['name'].lower()]
                    if system_devices:
                        recommended = system_devices[0]['name']
                        alternatives = [d['name'] for d in system_devices[1:]]
                
                # If still no recommendation, use any input device
                if not recommended and input_devices:
                    recommended = input_devices[0]['name']
                    alternatives = [d['name'] for d in input_devices[1:]]
                
                explanation = "For complete meeting recording, we recommend using a system audio capture device to record all participants."
            
            return {
                'recommended': recommended,
                'alternatives': alternatives[:3],  # Limit to top 3 alternatives
                'all_devices': [d['name'] for d in input_devices],
                'explanation': explanation
            }
            
        except Exception as e:
            logger.error(f"Error getting recommended devices: {str(e)}")
            return {
                'recommended': None,
                'alternatives': [],
                'all_devices': [],
                'explanation': "Unable to get device recommendations. Please select a device manually."
            }

# Helper function to check setup
def check_meeting_recorder_setup() -> Tuple[bool, str]:
    """
    Check if the meeting recorder can be properly set up.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Check for virtual audio
        va_success, va_message = VirtualAudioRecorder().setup_virtual_audio()
        
        # Check for whisper model
        whisper_success = True
        whisper_message = "Whisper transcription ready"
        try:
            transcriber = WhisperTranscriber(model_name="tiny.en")
            transcriber.load_model()  # Attempt to load the model
        except Exception as e:
            whisper_success = False
            whisper_message = f"Error loading Whisper model: {str(e)}"
        
        if va_success and whisper_success:
            return True, "Meeting recorder setup complete. Ready to record."
        else:
            return False, f"Meeting recorder setup issues:\n- Virtual Audio: {va_message}\n- Whisper: {whisper_message}"
            
    except Exception as e:
        logger.error(f"Error checking meeting recorder setup: {str(e)}")
        return False, f"Error checking meeting recorder setup: {str(e)}"
