import pytest
from audio_capture import AudioCapture

@pytest.fixture
def audio_capture():
    return AudioCapture()

def test_list_audio_devices(audio_capture):
    devices = audio_capture.list_audio_devices()
    assert isinstance(devices, list)
    # Devices may be empty on CI, but should not error

# Optionally, you can mock sounddevice for record_segment tests 