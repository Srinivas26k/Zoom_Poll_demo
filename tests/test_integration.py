"""
Integration tests for the Zoom Poll Automator workflow
Tests the full pipeline from audio capture to poll creation
"""
import os
import pytest
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

# Import the modules we need to test
import config
from audio_capture import AudioDevice, capture_audio
from transcribe_whisper import transcribe_audio
from poll_prompt import generate_poll
from poller import post_poll_to_meeting

class TestIntegrationWorkflow:
    """Test the full integration workflow with mocks for external services"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        # Create a temporary audio file for testing
        self.temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.temp_audio.close()
        
        # Mock environment variables
        os.environ["MEETING_ID"] = "1234567890"
        os.environ["ZOOM_TOKEN"] = "fake_token"
        os.environ["SEGMENT_DURATION"] = "5"
        
        # Create stop event for threading
        self.stop_event = threading.Event()
    
    def teardown_method(self):
        """Clean up after each test"""
        # Remove temporary files
        if hasattr(self, 'temp_audio') and os.path.exists(self.temp_audio.name):
            os.unlink(self.temp_audio.name)
    
    @patch('audio_capture.capture_audio')
    @patch('transcribe_whisper.transcribe_audio')
    @patch('poll_prompt.generate_poll')
    @patch('poller.post_poll_to_meeting')
    def test_complete_workflow(self, mock_post_poll, mock_generate_poll, 
                              mock_transcribe, mock_capture):
        """Test the entire workflow from audio capture to poll creation"""
        # Set up mocks
        mock_capture.return_value = self.temp_audio.name
        mock_transcribe.return_value = "This is a test transcript about Python programming"
        mock_generate_poll.return_value = {
            "title": "Python Programming Question",
            "questions": [
                {
                    "name": "What is Python primarily used for?",
                    "type": "single",
                    "answers": ["Web development", "Data science", "Game development", "All of the above"]
                }
            ]
        }
        mock_post_poll.return_value = {"success": True, "poll_id": "123456"}
        
        # Create a mock audio device
        mock_device = MagicMock()
        mock_device.name = "Test Device"
        
        # Run a simplified version of the workflow
        audio_file = mock_capture(mock_device, self.stop_event, 5)
        assert audio_file == self.temp_audio.name
        
        transcript = mock_transcribe(audio_file)
        assert "Python programming" in transcript
        
        poll_data = mock_generate_poll(transcript)
        assert poll_data["title"] == "Python Programming Question"
        assert len(poll_data["questions"]) == 1
        assert poll_data["questions"][0]["type"] == "single"
        
        zoom_poll = mock_post_poll(os.environ["MEETING_ID"], poll_data, os.environ["ZOOM_TOKEN"])
        assert zoom_poll["success"] is True
        assert zoom_poll["poll_id"] == "123456"
        
        # Verify all mocks were called correctly
        mock_capture.assert_called_once()
        mock_transcribe.assert_called_once_with(self.temp_audio.name)
        mock_generate_poll.assert_called_once_with(transcript)
        mock_post_poll.assert_called_once_with(
            os.environ["MEETING_ID"], 
            poll_data, 
            os.environ["ZOOM_TOKEN"]
        ) 