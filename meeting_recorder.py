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
import tempfile # Added for temporary segment filenames
import wave # Added for saving WAV files

from virtual_audio import VirtualAudioRecorder
from transcribe_whisper import WhisperTranscriber
# from poll_prompt import generate_poll # Removed
from poller import generate_poll_from_transcript # Added
from rich.console import Console
from ai_notes import AINotesGenerator, MeetingNote, ActionItem, MeetingSummary # Added

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

class MeetingRecorder:
    """
    Manages the end-to-end process of recording a meeting, transcribing the audio
    in near real-time, and generating AI-powered notes, summaries, and polls.

    Key functionalities include:
    - Segmented audio recording to allow for continuous transcription.
    - Queuing of audio segments for a dedicated transcription thread.
    - Real-time transcription using Whisper.
    - Periodic analysis of the transcript to generate meeting notes and polls.
    - Callbacks for updates on transcription, note generation, and poll creation.
    - Robust error handling and thread management for background tasks.
    """
    
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
        self.transcript = [] # This might be replaced by transcript_segments later
        self.transcript_lock = threading.Lock()
        self.segment_queue = queue.Queue() # Added
        self.segment_recording_thread = None # Added for the new recording thread
        
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

        # AI Notes Generator
        self.ai_notes_generator = AINotesGenerator()
        self.last_transcript_length_for_notes = 0
        self.final_meeting_summary_data = None

        # Thread health flags
        self.segment_recording_thread_active = False
        self.transcription_thread_active = False
        self.analysis_thread_active = False

    def _segment_recording_thread(self):
        """Records audio in segments and puts file paths to a queue."""
        segment_duration_seconds = 15
        samplerate = 16000
        channels = 1
        dtype = 'int16'
        max_retries = 3
        retry_delay = 1 # seconds

        try:
            while self.recording and not self.stop_event.is_set():
                if self.is_paused:
                    time.sleep(0.1)
                    continue

                audio_data = None
                for attempt in range(max_retries):
                    try:
                        # Record audio for segment_duration_seconds
                        audio_data = sd.rec(int(segment_duration_seconds * samplerate),
                                            samplerate=samplerate,
                                            channels=channels,
                                            dtype=dtype,
                                            blocking=True,
                                            device=self.device_index)
                        # sd.wait() # Not needed with blocking=True for sd.rec
                        break # Success
                    except sd.PortAudioError as pa_e:
                        logger.error(f"PortAudio error during sd.rec (attempt {attempt + 1}/{max_retries}): {pa_e}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                        else:
                            logger.critical(f"Persistent PortAudioError after {max_retries} attempts. Segment recording thread stopping.")
                            self.stop_event.set() # Signal other threads to stop as well due to critical error
                            return # Exit thread
                    except Exception as e_rec:
                        logger.error(f"Unexpected error during sd.rec (attempt {attempt + 1}/{max_retries}): {e_rec}", exc_info=True)
                        if attempt < max_retries - 1:
                             time.sleep(retry_delay)
                        else:
                            logger.critical(f"Persistent recording error after {max_retries} attempts. Segment recording thread stopping.")
                            self.stop_event.set() 
                            return # Exit thread
                
                if audio_data is None: # Should not happen if loop didn't return, but as safeguard
                    logger.warning("Audio data is None after recording attempts, skipping segment.")
                    continue

                try:
                    # Save to a temporary WAV file
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                        temp_file_path = tmp_file.name
                    
                    with wave.open(temp_file_path, 'wb') as wf:
                        wf.setnchannels(channels)
                        # Correctly get sample width using sounddevice's understanding of the dtype
                        sample_width = sd.check_input_settings(device=self.device_index, samplerate=samplerate, channels=channels, dtype=dtype).dtype.itemsize
                        wf.setsampwidth(sample_width)
                        wf.setframerate(samplerate)
                        wf.writeframes(audio_data.tobytes())
                    
                    self.segment_queue.put(temp_file_path)

                except Exception as e_file:
                    logger.error(f"Error saving audio segment to file {temp_file_path if 'temp_file_path' in locals() else 'unknown'}: {e_file}", exc_info=True)
                    # Clean up temp file if it was created but failed to write/queue
                    if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                        try:
                            os.remove(temp_file_path)
                        except OSError as ose:
                            logger.error(f"Error removing temporary segment file {temp_file_path} after save error: {ose}")
                    time.sleep(1) # Avoid rapid error looping on file errors

        except Exception as e:
            logger.error(f"Critical error in _segment_recording_thread ({threading.current_thread().name}): {e}", exc_info=True)
        finally:
            logger.info(f"_segment_recording_thread ({threading.current_thread().name}) stopped.")
            self.segment_recording_thread_active = False
        
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
        
    def start(self): # TODO: Review if this method is still needed or if start_recording is the primary entry point.
        """
        Simplified start method. Consider using start_recording for full functionality.
        Starts a basic recording session.
        """
        if self.is_recording:
            logger.warning("Recording already in progress (via simple start method)")
            return False
            
        self.is_recording = True
        self.is_paused = False
        self.start_time = datetime.now()
        
        # Start recording thread (old, to be removed)
        # self.recording_thread = threading.Thread(target=self._record_audio)
        # self.recording_thread.start()
        
        # Start processing thread (old, to be removed)
        # self.processing_thread = threading.Thread(target=self._process_audio)
        # self.processing_thread.start()
        
        # The new threads (_segment_recording_thread, _transcription_thread, _analysis_thread)
        # will be started in the revised start_recording method.
        
        logger.info(f"Recording started with device: {self.device_name}")
        return True
        
    def stop(self):
        """Stop recording"""
        if not self.is_recording:
            logger.warning("No recording in progress")
            return False
            
        self.is_recording = False
        self.is_paused = False
        
        # Wait for threads to finish (old, to be removed or replaced)
        # if self.recording_thread:
        #     self.recording_thread.join()
        # if self.processing_thread:
        #     self.processing_thread.join()
            
        # The new threads will be joined in the revised stop_recording method.
            
        # Save final transcript - This might be handled by _finalize_transcript
        # self._save_transcript() 
        
        logger.info("Recording stopped (via simple stop method)")
        return True
        
    def toggle_pause(self):
        """Toggle pause/resume recording"""
        if not self.is_recording:
            return False
            
        self.is_paused = not self.is_paused
        status = "paused" if self.is_paused else "resumed"
        logger.info(f"Recording {status}")
        return self.is_paused
        
    # Old methods _record_audio, _process_audio, _generate_transcript are fully removed.
    # _save_transcript method definition is removed as it's no longer used and did nothing.
            
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
            # Set device_index if provided
            if device_index is not None:
                self.device_index = device_index
            elif self.device_name: # if device_name was set in __init__
                self.device_index = self._get_device_index(self.device_name)
            else: # Fallback to default device if no specific device is set
                self.device_index = sd.default.device[0] # Default input device
            
            if self.device_index is None:
                 logger.error("No valid audio input device configured. Cannot start recording.")
                 return False

            logger.info(f"Using audio device index: {self.device_index} for recording.")

            # Create meeting directory
            meeting_dir = self.create_meeting_folder()
            
            # Reset state
            self.full_transcript = ""
            self.transcript_segments = []
            self.summary_notes = []
            self.auto_polls = []
            self.stop_event.clear()

            # Load Whisper model before starting threads
            try:
                logger.info("Loading Whisper model...")
                self.transcriber.load_model()
                logger.info("Whisper model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load Whisper model in start_recording: {e}", exc_info=True)
                return False # Prevent starting if model fails to load
            
            # Start audio recording (full recording file, if still needed alongside segments)
            # self.recording_file = self.audio_recorder.start_recording(self.device_index) # This might be redundant if segments cover all
            # if not self.recording_file:
            #     logger.error("Failed to start the main audio recorder. Aborting.")
            #     return False
            
            # Initialize output files
            self.transcript_file = str(meeting_dir / "transcript.txt") # For full transcript text
            # self.segments_file = str(meeting_dir / "transcript_segments.json") # Optional: if saving segments separately
            self.notes_file = str(meeting_dir / "notes.json")
            
            # Start processing threads
            self.recording = True
            self.transcribing = True # This flag might be controlled by transcription_thread status
            
            # Start audio recording (full recording)
            self.recording_file = self.audio_recorder.start_recording(self.device_index) # Keeps the full recording
            if not self.recording_file:
                logger.error("Failed to start the main audio recorder. Aborting.")
                self.recording = False
                return False

            # Start segment recording thread
            self.segment_recording_thread_active = True
            self.segment_recording_thread = threading.Thread(
                target=self._segment_recording_thread,
                daemon=True,
                name="SegmentRecordingThread"
            )
            self.segment_recording_thread.start()
            
            # Start transcription in a separate thread
            self.transcription_thread_active = True
            self.transcription_thread = threading.Thread(
                target=self._transcription_thread,
                daemon=True,
                name="TranscriptionThread"
            )
            self.transcription_thread.start()
            
            # Start analysis thread
            self.analysis_thread_active = True
            self.analysis_thread = threading.Thread(
                target=self._analysis_thread,
                daemon=True,
                name="AnalysisThread"
            )
            self.analysis_thread.start()
            
            logger.info(f"Started recording meeting {self.meeting_id} with all threads.")
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
            
            # Stop audio recording (full recording)
            if self.audio_recorder: # Ensure audio_recorder exists
                self.audio_recorder.stop_recording()
            
            # Wait for processing to complete (with timeout)
            if self.segment_recording_thread and self.segment_recording_thread.is_alive():
                logger.debug("Waiting for segment recording thread to join...")
                self.segment_recording_thread.join(timeout=5.0) # Short timeout as it should stop quickly
                if self.segment_recording_thread.is_alive():
                    logger.warning("Segment recording thread did not join in time.")
            
            if self.transcription_thread and self.transcription_thread.is_alive():
                logger.debug("Waiting for transcription thread to join...")
                self.transcription_thread.join(timeout=20.0) # Transcription might take longer
                if self.transcription_thread.is_alive():
                    logger.warning("Transcription thread did not join in time.")
            
            if self.analysis_thread and self.analysis_thread.is_alive():
                logger.debug("Waiting for analysis thread to join...")
                self.analysis_thread.join(timeout=10.0)
                if self.analysis_thread.is_alive():
                    logger.warning("Analysis thread did not join in time.")
            
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
            logger.info(f"Transcription thread ({threading.current_thread().name}) started.")
            
            while not self.stop_event.is_set() or not self.segment_queue.empty():
                try:
                    segment_file_path = self.segment_queue.get(timeout=1.0) # Wait for 1 sec
                    # console.print(f"[DEBUG] Got segment from queue: {segment_file_path}")

                    if segment_file_path is None: # Should not happen with current queue usage
                        continue

                    try:
                        # Transcribe the audio segment
                        # console.print(f"[DEBUG] Transcribing segment: {segment_file_path}")
                        result = self.transcriber.transcribe_audio(segment_file_path)
                        # console.print(f"[DEBUG] Transcription result: {result['text'][:50] if result else 'None'}")
                        
                        if result and "text" in result:
                            transcript_text = result["text"].strip()
                            if transcript_text:
                                # Add to full transcript
                                if self.full_transcript:
                                    self.full_transcript += " " + transcript_text # Append with a space
                                else:
                                    self.full_transcript = transcript_text
                                
                                # Add segment with timestamp
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                segment_entry = {
                                    "timestamp": timestamp,
                                    "text": transcript_text
                                }
                                self.transcript_segments.append(segment_entry)
                                
                                # self._save_transcript() # Call removed as per instruction 7 simplification
                                
                                # Notify listeners
                                if self.on_transcript_update:
                                    self.on_transcript_update(segment_entry, self.full_transcript)
                    
                    except Exception as e:
                        logger.error(f"Error transcribing audio segment {segment_file_path}: {str(e)}")
                    
                    finally:
                        # Delete the processed temporary segment file
                        try:
                            if os.path.exists(segment_file_path):
                                os.remove(segment_file_path)
                                # console.print(f"[DEBUG] Deleted segment file: {segment_file_path}")
                        except Exception as e:
                            logger.error(f"Error deleting segment file {segment_file_path}: {str(e)}")
                    
                    self.segment_queue.task_done()

                except queue.Empty:
                    # This is expected when the queue is empty and recording is still ongoing or stopping
                    if self.stop_event.is_set() and self.segment_queue.empty():
                        break # Exit if stop is signaled and queue is empty
                    continue # Continue waiting if not stopping
                except Exception as e:
                    logger.error(f"Error in transcription thread loop: {str(e)}")
                    # Avoid busy loop on unknown error
                    time.sleep(0.1)

            # The logic for final transcription of self.recording_file is removed here,
            # as segment-based transcription should cover the entire recording.
            # _finalize_transcript will save the accumulated self.full_transcript.
            
        except Exception as e:
            logger.error(f"Critical error in _transcription_thread ({threading.current_thread().name}): {e}", exc_info=True)
        finally:
            logger.info(f"_transcription_thread ({threading.current_thread().name}) stopped.")
            self.transcription_thread_active = False
    
    def _analysis_thread(self) -> None:
        """Thread that generates notes and polls based on transcript segments."""
        try:
            logger.info(f"Analysis thread ({threading.current_thread().name}) started.")
            
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
            logger.error(f"Critical error in _analysis_thread ({threading.current_thread().name}): {e}", exc_info=True)
        finally:
            logger.info(f"_analysis_thread ({threading.current_thread().name}) stopped.")
            self.analysis_thread_active = False
    
    def _generate_notes(self) -> None:
        """Generate meeting notes based on transcript segments."""
        NEW_CONTENT_THRESHOLD = 200  # Characters
        
        try:
            if len(self.full_transcript) > self.last_transcript_length_for_notes + NEW_CONTENT_THRESHOLD:
                new_transcript_segment = self.full_transcript[self.last_transcript_length_for_notes:]
                
                # logger.debug(f"Generating note for new segment: '{new_transcript_segment[:100]}...'")
                meeting_note_obj = self.ai_notes_generator.generate_note(new_transcript_segment)
                
                if meeting_note_obj and meeting_note_obj.content and "Empty transcript segment" not in meeting_note_obj.content:
                    note_dict = meeting_note_obj.to_dict()
                    self.summary_notes.append(note_dict)
                    self.last_transcript_length_for_notes = len(self.full_transcript)
                    
                    self._save_notes()  # Save notes after each new note
                    
                    if self.on_note_generated:
                        self.on_note_generated(note_dict, self.summary_notes)
                    
                    logger.info(f"Generated and saved meeting note at {meeting_note_obj.timestamp}")
                # else:
                    # logger.debug("Note generation skipped or returned empty.")
            # else:
                # logger.debug(f"Not enough new content for notes. Current: {len(self.full_transcript)}, Last: {self.last_transcript_length_for_notes}")

        except Exception as e:
            logger.error(f"Error generating meeting notes: {str(e)}")
    
    def _generate_poll(self) -> None:
        """Generate a poll based on the transcript content."""
        if not self.full_transcript or len(self.full_transcript) < 100:
            logger.debug("Not enough transcript content for poll generation")
            return
        
        try:
            # Call poll generation function from poller.py
            title, question, options = generate_poll_from_transcript(self.full_transcript)
            
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
            logger.warning("Notes file path not set. Cannot save notes.")
            return
        
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            if self.final_meeting_summary_data and self.final_meeting_summary_data.get('date'):
                current_date = self.final_meeting_summary_data['date']

            data_to_save = {
                "meeting_id": self.meeting_id,
                "date": current_date,
                "interim_notes": self.summary_notes, # These are incrementally generated notes
                "polls": self.auto_polls,
                "final_summary": self.final_meeting_summary_data # This will be None until _generate_final_summary
            }
            
            with open(self.notes_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved meeting data to {self.notes_file}")
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
            logger.info(f"Generating final meeting summary for meeting ID: {self.meeting_id}")
            summary_obj = self.ai_notes_generator.generate_meeting_summary(self.meeting_id, self.full_transcript)
            
            if summary_obj:
                self.final_meeting_summary_data = summary_obj.to_dict()
                
                # Replace interim notes with notes from the final summary
                if summary_obj.notes: # Ensure notes exist and are iterable
                    self.summary_notes = [
                        note.to_dict() if isinstance(note, MeetingNote) else note 
                        for note in summary_obj.notes
                    ]
                else:
                    self.summary_notes = [] # Clear if no notes in summary
                
                # Optional: Process action items if needed elsewhere
                # if summary_obj.action_items:
                #     # Example: self.action_items_list = [item.to_dict() for item in summary_obj.action_items]
                #     pass

                self._save_notes() # Persist the final summary and updated notes
                logger.info("Generated and saved final meeting summary.")
            else:
                logger.warning("Failed to generate final meeting summary.")
                # Fallback: Keep interim notes if final summary fails.
                # No need to call _save_notes() here if nothing changed or if we want to keep interim notes as primary.

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
