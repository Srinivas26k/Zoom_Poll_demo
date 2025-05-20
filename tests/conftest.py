import os
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Set up test environment variables
os.environ["LLAMA_HOST"] = "http://localhost:11434"
os.environ["ZOOM_TOKEN"] = "test_token" 