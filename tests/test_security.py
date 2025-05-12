"""
Security tests for the Zoom Poll Automator
Tests credential handling, token security, and API access
"""
import pytest
import os
import re
import logging
from unittest.mock import patch, MagicMock

import config
from app import app as flask_app

@pytest.fixture
def client():
    """Flask test client"""
    with flask_app.test_client() as client:
        yield client

class TestSecurity:
    """Test security aspects of the application"""
    
    def test_env_file_not_committed(self):
        """Verify .env is in .gitignore to prevent credential leakage"""
        with open('.gitignore', 'r') as f:
            gitignore_content = f.read()
        
        # Check if .env is explicitly mentioned in .gitignore
        assert '.env' in gitignore_content, ".env should be listed in .gitignore"
    
    @patch('logging.Logger.info')
    @patch('logging.Logger.error')
    def test_no_credentials_in_logs(self, mock_error, mock_info):
        """Test that sensitive credentials are not logged"""
        # Set up environment with sensitive data
        os.environ['CLIENT_ID'] = 'test_sensitive_id'
        os.environ['CLIENT_SECRET'] = 'test_sensitive_secret'
        
        # Call functions that might log
        try:
            config.validate_config()
        except:
            pass
        
        # Check all logged messages
        for args, _ in mock_info.call_args_list:
            for arg in args:
                assert 'test_sensitive_id' not in str(arg), "CLIENT_ID leaked in logs"
                assert 'test_sensitive_secret' not in str(arg), "CLIENT_SECRET leaked in logs"
        
        for args, _ in mock_error.call_args_list:
            for arg in args:
                assert 'test_sensitive_id' not in str(arg), "CLIENT_ID leaked in logs"
                assert 'test_sensitive_secret' not in str(arg), "CLIENT_SECRET leaked in logs"
    
    def test_secret_key_generation(self):
        """Test that a strong secret key is generated"""
        # Remove existing key if present
        if 'FLASK_SECRET_KEY' in os.environ:
            del os.environ['FLASK_SECRET_KEY']
        
        # Generate a new key via the config module
        original_secret_key = os.environ.get('SECRET_TOKEN')
        try:
            os.environ['SECRET_TOKEN'] = None
            with patch('os.urandom') as mock_urandom:
                # Simulate a high-entropy random value
                mock_urandom.return_value = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10'
                
                # Reload config to trigger key generation
                reload_result = config.setup_config()
                
                # The function should have called os.urandom
                mock_urandom.assert_called()
        finally:
            # Restore original value
            if original_secret_key:
                os.environ['SECRET_TOKEN'] = original_secret_key
            else:
                if 'SECRET_TOKEN' in os.environ:
                    del os.environ['SECRET_TOKEN']
    
    def test_token_storage_in_session(self, client):
        """Test that tokens are stored securely in the session"""
        with client.session_transaction() as session:
            session['access_token'] = 'test_token'
            session['token_expires_at'] = 9999999999  # Far future
        
        # Access a protected route
        response = client.get('/setup')
        
        # Check that the session works but token is not exposed
        assert response.status_code == 200
        assert b'test_token' not in response.data
    
    @patch('requests.post')
    def test_https_used_for_api_calls(self, mock_post):
        """Test that HTTPS is used for all API calls"""
        from poller import create_poll_in_meeting
        
        # Setup the mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test_poll_id"}
        mock_post.return_value = mock_response
        
        # Call the function that makes API requests
        poll_data = {
            "title": "Test Poll",
            "questions": [{"name": "Q1", "type": "single", "answers": ["A", "B"]}]
        }
        create_poll_in_meeting("123456789", poll_data, "test_token")
        
        # Verify all calls used HTTPS
        for call in mock_post.call_args_list:
            url = call[0][0]
            assert url.startswith('https://'), f"API call to {url} does not use HTTPS"
    
    def test_input_validation(self, client):
        """Test that user inputs are validated to prevent injection attacks"""
        # Try with a potential SQL injection in the meeting_id
        response = client.post('/setup', data={
            'device': 'Default Device',
            'meeting_id': "123456789' OR '1'='1",
            'segment_duration': '30'
        })
        
        # Should be redirected or show an error, not 500 server error
        assert response.status_code != 500, "Server error occurred with malicious input" 