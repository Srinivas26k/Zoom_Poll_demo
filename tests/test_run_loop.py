"""
Tests for the run_loop module that drives the main automation loop
"""
import os
import time
import threading
import pytest
from unittest.mock import patch, MagicMock

import run_loop

class TestRunLoop:
    """Test the main automation loop functionality"""
    
    @patch('run_loop.capture_audio')
    @patch('run_loop.transcribe_audio')
    @patch('run_loop.generate_poll')
    @patch('run_loop.create_poll_in_meeting')
    def test_run_loop_iteration(self, mock_create_poll, mock_generate_poll, 
                                mock_transcribe, mock_capture):
        """Test that a single run loop iteration works correctly"""
        # Setup mocks
        mock_capture.return_value = "test_audio.wav"
        mock_transcribe.return_value = "Test transcript about data science"
        mock_generate_poll.return_value = {
            "title": "Data Science Poll",
            "questions": [{"name": "Test question", "type": "single", "answers": ["A", "B", "C"]}]
        }
        mock_create_poll.return_value = {"success": True}
        
        # Setup environment
        os.environ["SEGMENT_DURATION"] = "5"
        os.environ["MEETING_ID"] = "test123"
        os.environ["ZOOM_TOKEN"] = "test_token"
        
        # Create stop event
        stop_event = threading.Event()
        
        # Create a mock device
        mock_device = MagicMock()
        mock_device.name = "Test Device"
        
        # Test a single iteration, setting stop event after one iteration
        def set_stop_after_delay():
            time.sleep(0.5)  # Short delay
            stop_event.set()
        
        # Start thread to stop the loop
        threading.Thread(target=set_stop_after_delay).start()
        
        # Run the loop
        run_loop.run_loop(mock_device, stop_event)
        
        # Verify mocks were called
        mock_capture.assert_called_once()
        mock_transcribe.assert_called_once_with("test_audio.wav")
        mock_generate_poll.assert_called_once()
        mock_create_poll.assert_called_once()

    @patch('run_loop.capture_audio')
    def test_run_loop_stop_event(self, mock_capture):
        """Test that the run loop stops when the stop event is set"""
        # Set stop event immediately
        stop_event = threading.Event()
        stop_event.set()
        
        # Create a mock device
        mock_device = MagicMock()
        mock_device.name = "Test Device"
        
        # Run the loop
        run_loop.run_loop(mock_device, stop_event)
        
        # Verify capture_audio was not called
        mock_capture.assert_not_called()

    @patch('run_loop.capture_audio')
    @patch('run_loop.logger')
    def test_run_loop_exception_handling(self, mock_logger, mock_capture):
        """Test that exceptions in the run loop are properly handled"""
        # Setup mock to raise an exception
        mock_capture.side_effect = Exception("Test exception")
        
        # Setup environment
        os.environ["SEGMENT_DURATION"] = "5"
        
        # Create stop event (set after first iteration)
        stop_event = threading.Event()
        
        # Create a mock device
        mock_device = MagicMock()
        mock_device.name = "Test Device"
        
        def set_stop_after_delay():
            time.sleep(0.5)  # Short delay
            stop_event.set()
        
        # Start thread to stop the loop
        threading.Thread(target=set_stop_after_delay).start()
        
        # Run the loop
        run_loop.run_loop(mock_device, stop_event)
        
        # Verify logger.error was called
        mock_logger.error.assert_called() 