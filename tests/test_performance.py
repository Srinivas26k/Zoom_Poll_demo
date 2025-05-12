"""
Performance tests for the Zoom Poll Automator components
"""
import pytest
import time
import psutil
import os
import tempfile
from unittest.mock import patch, MagicMock

from poll_prompt import generate_poll
from transcribe_whisper import transcribe_audio

class TestPerformance:
    """Test performance characteristics of key components"""
    
    @pytest.fixture
    def create_sample_audio(self):
        """Create a sample audio file of specific length for testing"""
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file.close()
        
        # Generate a simple WAV file using Python's wave module
        import wave
        import struct
        import array
        
        # 1-second WAV file at 16kHz
        duration = 5  # seconds
        sample_rate = 16000
        num_samples = duration * sample_rate
        
        with wave.open(temp_file.name, 'w') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 2 bytes (16 bits)
            wav_file.setframerate(sample_rate)
            
            # Generate a simple tone
            amplitude = 32767 / 2  # Half max amplitude for 16-bit audio
            frequency = 440.0  # A4 note
            
            # Write the samples
            for i in range(num_samples):
                t = float(i) / sample_rate
                value = int(amplitude * (1 + 0.5 * (time.time() % 2)))
                packed_value = struct.pack('h', value)
                wav_file.writeframes(packed_value)
                
        yield temp_file.name
        
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    
    @patch('transcribe_whisper.whisper')
    def test_transcription_speed(self, mock_whisper, create_sample_audio):
        """Test that transcription completes within reasonable time"""
        # Mock the Whisper model
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "This is a test transcription"
        }
        mock_whisper.load_model.return_value = mock_model
        
        # Measure transcription time
        audio_file = create_sample_audio
        start_time = time.time()
        transcribe_audio(audio_file)
        end_time = time.time()
        
        # Check if transcription time is reasonable
        # For 5 seconds of audio, transcription should happen within 10 seconds
        assert end_time - start_time < 10, f"Transcription took too long: {end_time - start_time:.2f} seconds"
    
    @patch('poll_prompt.requests.post')
    def test_poll_generation_performance(self, mock_post):
        """Test poll generation performance"""
        # Mock the LLM API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": '{"title":"Test Poll","questions":[{"name":"Test Question","type":"single","answers":["A","B","C","D"]}]}'
        }
        mock_post.return_value = mock_response
        
        # Set required environment variable
        os.environ["LLAMA_HOST"] = "http://localhost:11434"
        
        # Measure generation time
        transcript = "This is a test transcript about various topics in technology."
        start_time = time.time()
        generate_poll(transcript)
        end_time = time.time()
        
        # Check if generation time is reasonable (less than 5 seconds)
        assert end_time - start_time < 5, f"Poll generation took too long: {end_time - start_time:.2f} seconds"
    
    def test_memory_usage(self):
        """Test memory usage during operation"""
        # Get baseline memory usage
        baseline = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        
        # Perform a memory-intensive operation
        large_data = ["x" * 1000000 for _ in range(10)]  # ~10MB of data
        
        # Check memory usage after the operation
        current = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        increase = current - baseline
        
        # Memory increase should be reasonable
        assert increase < 20, f"Memory usage increase too high: {increase:.2f} MB"
        
        # Clean up
        del large_data
    
    @patch('poll_prompt.requests.post')
    def test_concurrent_poll_generation(self, mock_post):
        """Test performance with concurrent poll generation requests"""
        # Mock the LLM API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": '{"title":"Test Poll","questions":[{"name":"Test Question","type":"single","answers":["A","B","C","D"]}]}'
        }
        mock_post.return_value = mock_response
        
        # Set required environment variable
        os.environ["LLAMA_HOST"] = "http://localhost:11434"
        
        import threading
        import queue
        
        # Queue for storing results
        result_queue = queue.Queue()
        
        # Function to generate poll and put result in queue
        def generate_and_queue(transcript, q):
            result = generate_poll(transcript)
            q.put(result)
        
        # Create and start threads
        threads = []
        start_time = time.time()
        
        for i in range(3):  # Generate 3 polls concurrently
            transcript = f"This is test transcript {i} about various topics."
            thread = threading.Thread(target=generate_and_queue, args=(transcript, result_queue))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Check results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())
        
        # We should have 3 results
        assert len(results) == 3
        
        # Total time should be reasonable for concurrent operations
        # If operations were fully sequential, it would take ~3x longer
        assert end_time - start_time < 5, f"Concurrent generation took too long: {end_time - start_time:.2f} seconds" 