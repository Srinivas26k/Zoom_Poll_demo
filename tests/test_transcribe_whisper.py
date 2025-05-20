import pytest
import os
from transcribe_whisper import WhisperTranscriber

@pytest.fixture(scope="module")
def whisper():
    return WhisperTranscriber(model_name="tiny")

def test_load_model(whisper):
    whisper.load_model()
    assert whisper.model is not None

def test_transcribe_audio_file_not_found(whisper):
    with pytest.raises(FileNotFoundError):
        whisper.transcribe_audio("nonexistent.wav")

def test_transcribe_audio_success(whisper, tmp_path):
    # Create a short silent wav file for test
    import numpy as np
    import soundfile as sf
    test_file = tmp_path / "test.wav"
    data = np.zeros(16000)  # 1 second of silence at 16kHz
    sf.write(str(test_file), data, 16000)
    whisper.load_model()
    result = whisper.transcribe_audio(str(test_file))
    assert isinstance(result, dict)
    assert "text" in result 