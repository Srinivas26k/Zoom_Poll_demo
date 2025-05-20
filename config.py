# config.py
import os
import logging
import shutil
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_env_file(env_path: str) -> bool:
    """Load environment variables from a file."""
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"Loaded environment from {env_path}")
        return True
    return False

def create_env_from_example():
    """Create .env file from .env.example if it doesn't exist."""
    env_path = Path(".env")
    example_path = Path(".env.example")
    
    if not env_path.exists() and example_path.exists():
        try:
            shutil.copy(example_path, env_path)
            logger.info(f"Created .env from .env.example")
            load_dotenv()
            return True
        except Exception as e:
            logger.error(f"Failed to create .env from example: {str(e)}")
            return False
    return False

def validate_config() -> Dict[str, Any]:
    """Validate required configuration values."""
    required_vars = {
        "CLIENT_ID": "Zoom API Client ID",
        "CLIENT_SECRET": "Zoom API Client Secret",
        "REDIRECT_URI": "OAuth Redirect URI",
    }
    
    missing_vars = []
    config = {}
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"{description} ({var})")
        config[var] = value
    
    if missing_vars:
        error_msg = f"Missing required configuration: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    return config

def setup_config() -> None:
    """Setup configuration with fallback to .env.example."""
    # Try loading .env first
    if not load_env_file(".env"):
        # If .env doesn't exist, try creating from .env.example
        if create_env_from_example():
            logger.info("Created and loaded .env from .env.example")
        # If still can't create, try loading .env.example directly
        elif load_env_file(".env.example"):
            logger.warning("Using .env.example as .env file not found")
        else:
            logger.error("Neither .env nor .env.example found")
            raise FileNotFoundError("No environment configuration file found")

    # Validate configuration
    config = validate_config()
    
    # Set global variables
    global CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, FLASK_SECRET_KEY, VERIFICATION_TOKEN
    global LLAMA_HOST_BASE, LLAMA_HOST, OLLAMA_API
    
    CLIENT_ID = config["CLIENT_ID"]
    CLIENT_SECRET = config["CLIENT_SECRET"]
    REDIRECT_URI = config["REDIRECT_URI"]
    
    # Use SECRET_TOKEN as FLASK_SECRET_KEY if available, otherwise generate a random one
    SECRET_TOKEN = os.getenv("SECRET_TOKEN")
    FLASK_SECRET_KEY = SECRET_TOKEN or os.urandom(24).hex()
    VERIFICATION_TOKEN = os.getenv("VERIFICATION_TOKEN")
    
    # Extract Ollama host from env, ensuring it's properly formatted
    LLAMA_HOST_BASE = os.getenv("LLAMA_HOST", "http://localhost:11434").rstrip('/')
    LLAMA_HOST = f"{LLAMA_HOST_BASE}/v1"  # For OpenAI client compatibility
    OLLAMA_API = LLAMA_HOST_BASE  # For direct Ollama API calls