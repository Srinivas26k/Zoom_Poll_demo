import pytest
from unittest.mock import Mock, patch
from poller import (
    generate_poll_with_llama,
    extract_key_topics,
    clean_text,
    is_meaningful_text,
    extract_json_from_text
)

@pytest.fixture
def sample_transcript():
    return """
    In today's meeting, we discussed the new product launch strategy.
    The team proposed three options: launching in Q1, Q2, or Q3.
    Marketing suggested Q1 for better market timing, while Sales preferred Q2.
    Engineering recommended Q3 to ensure product readiness.
    """

@pytest.fixture
def mock_llama_response():
    return {
        "response": '''{
            "title": "Product Launch Timing Decision",
            "question": "When should we launch the new product?",
            "options": [
                "Q1 - Better market timing",
                "Q2 - Sales team preference",
                "Q3 - Engineering recommendation",
                "Need more discussion"
            ]
        }'''
    }

def test_is_meaningful_text():
    """Test text meaningfulness validation."""
    assert is_meaningful_text("This is a meaningful text with several words")
    assert not is_meaningful_text("")
    assert not is_meaningful_text("a b c")
    assert not is_meaningful_text("   ")

def test_clean_text():
    """Test text cleaning functionality."""
    text = "  Hello,   this is a test.  Um, you know, like...  "
    cleaned = clean_text(text)
    assert "  " not in cleaned
    assert "um" not in cleaned.lower()
    assert "you know" not in cleaned.lower()

def test_extract_key_topics(sample_transcript):
    """Test key topic extraction."""
    topics = extract_key_topics(sample_transcript)
    assert isinstance(topics, str)
    assert len(topics.split(",")) > 0
    # Check for expected keywords
    assert any(word in topics.lower() for word in ["product", "launch", "strategy"])

def test_extract_json_from_text():
    """Test JSON extraction from text."""
    text = "Some text before {\"key\": \"value\"} some text after"
    result = extract_json_from_text(text)
    assert result == {"key": "value"}
    
    # Test with invalid JSON
    assert extract_json_from_text("No JSON here") is None

@patch('poller.requests.post')
def test_generate_poll_with_llama(mock_post, sample_transcript, mock_llama_response):
    """Test poll generation with mocked LLaMA response."""
    mock_post.return_value.json.return_value = mock_llama_response
    mock_post.return_value.status_code = 200
    
    with patch('poller.config.LLAMA_HOST', 'http://localhost:11434'):
        result = generate_poll_with_llama(sample_transcript)
        
        assert result is not None
        assert "title" in result
        assert "question" in result
        assert "options" in result
        assert len(result["options"]) == 4
        
        # Verify the poll is relevant to the transcript
        assert "launch" in result["title"].lower()
        assert "product" in result["title"].lower()

def test_generate_poll_with_short_transcript():
    """Test poll generation with insufficient content."""
    result = generate_poll_with_llama("Too short")
    assert result is None

@patch('poller.requests.post')
def test_generate_poll_api_error(mock_post, sample_transcript):
    """Test poll generation with API error."""
    mock_post.return_value.status_code = 500
    mock_post.return_value.text = "Internal Server Error"
    
    with patch('poller.config.LLAMA_HOST', 'http://localhost:11434'):
        result = generate_poll_with_llama(sample_transcript)
        assert result is None

def test_generate_poll_without_llama_host():
    """Test poll generation without LLaMA host configuration."""
    result = generate_poll_with_llama("Test transcript")
    assert result is None 