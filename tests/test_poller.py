import pytest
from poller import generate_poll_from_transcript

def test_generate_poll_from_empty_transcript():
    title, question, options = generate_poll_from_transcript("")
    assert isinstance(title, str)
    assert isinstance(question, str)
    assert isinstance(options, list)
    assert len(options) == 4

def test_generate_poll_from_sample_transcript():
    transcript = "Today we discussed project deadlines and next steps."
    title, question, options = generate_poll_from_transcript(transcript)
    assert isinstance(title, str)
    assert isinstance(question, str)
    assert isinstance(options, list)
    assert len(options) == 4 