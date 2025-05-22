#!/usr/bin/env python
import os
import sys
import pytest

def main():
    """Run the test suite."""
    # Add project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Set up test environment
    os.environ["LLAMA_HOST"] = "http://localhost:11434"
    os.environ["ZOOM_TOKEN"] = "test_token"
    
    # Run tests
    args = [
        "tests/",
        "-v",
        "--cov=.",
        "--cov-report=term-missing",
        "--cov-report=xml",
    ]
    
    # Add any command line arguments
    args.extend(sys.argv[1:])
    
    return pytest.main(args)

if __name__ == "__main__":
    sys.exit(main()) 