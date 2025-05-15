"""
Pytest configuration file for shared fixtures
"""
import os
import pytest
import tempfile
from unittest.mock import MagicMock

@pytest.fixture(scope="function")
def setup_env_vars():
    """Set up environment variables needed for tests"""
    # Save original env vars
    original_env = {}
    for var in ["CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI", "MEETING_ID", 
                "ZOOM_TOKEN", "SEGMENT_DURATION", "LLAMA_HOST"]:
        original_env[var] = os.environ.get(var)
    
    # Set test env vars
    os.environ["CLIENT_ID"] = "test_client_id"
    os.environ["CLIENT_SECRET"] = "test_client_secret"
    os.environ["REDIRECT_URI"] = "http://localhost:8000/oauth/callback"
    os.environ["MEETING_ID"] = "1234567890"
    os.environ["ZOOM_TOKEN"] = "test_token"
    os.environ["SEGMENT_DURATION"] = "5"
    os.environ["LLAMA_HOST"] = "http://localhost:11434"
    
    yield
    
    # Restore original env vars
    for var, value in original_env.items():
        if value is None:
            if var in os.environ:
                del os.environ[var]
        else:
            os.environ[var] = value

@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing"""
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)

@pytest.fixture
def mock_audio_device():
    """Create a mock audio device for testing"""
    device = MagicMock()
    device.name = "Test Audio Device"
    device.index = 0
    return device

@pytest.fixture
def mock_zoom_response():
    """Create a mock successful Zoom API response"""
    return {
        "id": "test_poll_id",
        "status": "active",
        "questions": [
            {
                "name": "Test Question",
                "type": "single",
                "answers": ["Option A", "Option B", "Option C", "Option D"]
            }
        ]
    }

@pytest.fixture
def sample_poll_data():
    """Sample poll data for testing"""
    return {
        "title": "Sample Poll",
        "questions": [
            {
                "name": "What is your favorite programming language?",
                "type": "single",
                "answers": ["Python", "JavaScript", "Java", "C++"]
            }
        ]
    }

@pytest.fixture
def sample_transcript():
    """Sample transcript for testing"""
    return """
    Welcome everyone to our session on programming languages.
    Today we'll discuss the pros and cons of Python, JavaScript, Java, and C++.
    Python is known for its readability and extensive libraries.
    JavaScript is essential for web development.
    Java is widely used in enterprise applications.
    C++ offers great performance for system programming.
    """ 