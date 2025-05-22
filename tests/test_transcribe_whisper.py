import pytest
import os
from unittest.mock import Mock, patch
from transcribe_whisper import WhisperTranscriber

@pytest.fixture
def mock_whisper_model():
    with patch('whisper.load_model') as mock:
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "This is a test transcription.",
            "segments": [{"text": "This is a test transcription."}]
        }
        mock.return_value = mock_model
        yield mock

@pytest.fixture
def transcriber(mock_whisper_model):
    return WhisperTranscriber(model_name="base")

def test_transcriber_initialization():
    """Test transcriber initialization with different devices."""
    with patch('torch.cuda.is_available', return_value=True):
        transcriber = WhisperTranscriber()
        assert transcriber.device == "cuda"
    
    with patch('torch.cuda.is_available', return_value=False):
        transcriber = WhisperTranscriber()
        assert transcriber.device == "cpu"

def test_load_model(transcriber, mock_whisper_model):
    """Test model loading functionality."""
    transcriber.load_model()
    mock_whisper_model.assert_called_once_with("base", device=transcriber.device)
    assert transcriber.model is not None

def test_transcribe_audio(transcriber, mock_whisper_model, tmp_path):
    """Test audio transcription functionality."""
    # Create a temporary audio file
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"dummy audio content")
    
    result = transcriber.transcribe_audio(str(audio_file))
    assert result["text"] == "This is a test transcription."
    mock_whisper_model.return_value.transcribe.assert_called_once()

def test_transcribe_audio_file_not_found(transcriber):
    """Test transcription with non-existent file."""
    with pytest.raises(FileNotFoundError):
        transcriber.transcribe_audio("nonexistent.wav")

def test_get_temp_file_path(transcriber):
    """Test temporary file path generation."""
    temp_path = transcriber.get_temp_file_path()
    assert temp_path.startswith(os.path.join(os.path.dirname(temp_path), "zoom_audio_"))
    assert temp_path.endswith(".wav")

def test_cleanup(transcriber, mock_whisper_model):
    """Test resource cleanup."""
    transcriber.load_model()
    transcriber.cleanup()
    assert transcriber.model is None 