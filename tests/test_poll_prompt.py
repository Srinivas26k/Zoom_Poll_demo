"""
Tests for the poll_prompt module that generates poll questions from transcripts
"""
import pytest
from unittest.mock import patch, MagicMock
import json
import os

import poll_prompt
from poll_prompt import generate_poll

class TestPollPrompt:
    """Test poll generation functionality"""
    
    @patch('poll_prompt.requests.post')
    def test_generate_poll_success(self, mock_post):
        """Test successful poll generation from transcript"""
        # Sample valid response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": json.dumps({
                "title": "Technology Trends Poll",
                "questions": [
                    {
                        "name": "Which technology trend is most relevant to your work?",
                        "type": "single",
                        "answers": [
                            "Artificial Intelligence",
                            "Blockchain",
                            "Cloud Computing",
                            "Internet of Things"
                        ]
                    }
                ]
            })
        }
        mock_post.return_value = mock_response
        
        # Set required environment variable
        os.environ["LLAMA_HOST"] = "http://localhost:11434"
        
        # Test poll generation
        transcript = "Today we're discussing technology trends including AI, blockchain, cloud, and IoT."
        result = generate_poll(transcript)
        
        # Verify result
        assert result["title"] == "Technology Trends Poll"
        assert len(result["questions"]) == 1
        assert result["questions"][0]["type"] == "single"
        assert len(result["questions"][0]["answers"]) == 4
        
        # Verify the request was made correctly
        mock_post.assert_called_once()
        assert "model" in mock_post.call_args[1]["json"]
        assert "prompt" in mock_post.call_args[1]["json"]
    
    @patch('poll_prompt.requests.post')
    def test_generate_poll_invalid_response(self, mock_post):
        """Test handling of invalid model responses"""
        # Non-JSON response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Not valid JSON"}
        mock_post.return_value = mock_response
        
        # Set required environment variable
        os.environ["LLAMA_HOST"] = "http://localhost:11434"
        
        # Test with invalid response
        transcript = "Test transcript"
        result = generate_poll(transcript)
        
        # Should fall back to default poll structure
        assert "title" in result
        assert "questions" in result
        assert len(result["questions"]) > 0
    
    @patch('poll_prompt.requests.post')
    def test_generate_poll_error_handling(self, mock_post):
        """Test error handling when API request fails"""
        # Simulate connection error
        mock_post.side_effect = Exception("Connection error")
        
        # Set required environment variable
        os.environ["LLAMA_HOST"] = "http://localhost:11434"
        
        # Test error handling
        transcript = "Test transcript"
        result = generate_poll(transcript)
        
        # Should fall back to default poll
        assert "title" in result
        assert "questions" in result
        assert "Error" in result["title"]
    
    @patch('poll_prompt.requests.post')
    def test_generate_poll_content_validation(self, mock_post):
        """Test that generated poll content is validated"""
        # Response missing required fields
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": json.dumps({
                "title": "Incomplete Poll",
                # Missing "questions" field
            })
        }
        mock_post.return_value = mock_response
        
        # Set required environment variable
        os.environ["LLAMA_HOST"] = "http://localhost:11434"
        
        # Test with incomplete response
        transcript = "Test transcript"
        result = generate_poll(transcript)
        
        # Should fall back to default poll with questions field
        assert "questions" in result

    @patch('poll_prompt.requests.post')
    def test_generate_poll_missing_title(self, mock_post):
        """Test handling of poll generation when title is missing"""
        # Sample valid response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": json.dumps({
                "questions": [
                    {
                        "name": "Which technology trend is most relevant to your work?",
                        "type": "single",
                        "answers": [
                            "Artificial Intelligence",
                            "Blockchain",
                            "Cloud Computing",
                            "Internet of Things"
                        ]
                    }
                ]
            })
        }
        mock_post.return_value = mock_response
        
        # Set required environment variable
        os.environ["LLAMA_HOST"] = "http://localhost:11434"
        
        # Test poll generation
        transcript = "Today we're discussing technology trends including AI, blockchain, cloud, and IoT."
        result = generate_poll(transcript)
        
        # Verify result
        assert result["title"] == "Technology Trends Poll"
        assert len(result["questions"]) == 1
        assert result["questions"][0]["type"] == "single"
        assert len(result["questions"][0]["answers"]) == 4
        
        # Verify the request was made correctly
        mock_post.assert_called_once()
        assert "model" in mock_post.call_args[1]["json"]
        assert "prompt" in mock_post.call_args[1]["json"]

    @patch('poll_prompt.requests.post')
    def test_generate_poll_missing_questions(self, mock_post):
        """Test handling of poll generation when questions are missing"""
        # Sample valid response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": json.dumps({
                "title": "Technology Trends Poll"
            })
        }
        mock_post.return_value = mock_response
        
        # Set required environment variable
        os.environ["LLAMA_HOST"] = "http://localhost:11434"
        
        # Test poll generation
        transcript = "Today we're discussing technology trends including AI, blockchain, cloud, and IoT."
        result = generate_poll(transcript)
        
        # Verify result
        assert result["title"] == "Technology Trends Poll"
        assert len(result["questions"]) == 1
        assert result["questions"][0]["type"] == "single"
        assert len(result["questions"][0]["answers"]) == 4
        
        # Verify the request was made correctly
        mock_post.assert_called_once()
        assert "model" in mock_post.call_args[1]["json"]
        assert "prompt" in mock_post.call_args[1]["json"] 