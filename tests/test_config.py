import pytest
import os
import config

def test_validate_config_success(monkeypatch):
    monkeypatch.setenv("CLIENT_ID", "testid")
    monkeypatch.setenv("CLIENT_SECRET", "testsecret")
    monkeypatch.setenv("REDIRECT_URI", "http://localhost:8000/oauth/callback")
    result = config.validate_config()
    assert isinstance(result, dict)
    assert result["CLIENT_ID"] == "testid"

def test_validate_config_missing(monkeypatch):
    monkeypatch.delenv("CLIENT_ID", raising=False)
    monkeypatch.delenv("CLIENT_SECRET", raising=False)
    monkeypatch.delenv("REDIRECT_URI", raising=False)
    with pytest.raises(ValueError):
        config.validate_config() 