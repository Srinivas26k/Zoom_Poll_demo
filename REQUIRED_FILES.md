# Required Files for Zoom Poll Automator

## Core Python Files
1. `app.py` - Main Flask application
2. `config.py` - Configuration management
3. `poller.py` - Zoom poll creation and management
4. `transcribe_whisper.py` - Audio transcription using Whisper
5. `audio_capture.py` - Audio capture functionality
6. `poll_prompt.py` - Poll generation logic
7. `run_loop.py` - Main execution loop
8. `cli.py` - Command-line interface
9. `run.py` - Application runner

## Essential Batch Files
1. `run_tests.bat` - Main test runner
2. `setup.bat` - Project setup script
3. `start.bat` - Application starter

## Configuration Files
1. `requirements.txt` - Python dependencies
2. `pytest.ini` - Pytest configuration
3. `.gitignore` - Git ignore rules

## Documentation
1. `README.md` - Project documentation
2. `test_results_summary.md` - Test results summary

## Test Files
1. `tests/test_integration.py` - Integration tests
2. `tests/test_performance.py` - Performance tests
3. `tests/test_security.py` - Security tests
4. `tests/test_app_smoke.py` - Smoke tests
5. `tests/test_audio_capture.py` - Audio capture tests
6. `tests/test_config.py` - Configuration tests
7. `tests/test_poll_prompt.py` - Poll generation tests
8. `tests/test_poller.py` - Poller tests
9. `tests/test_transcribe_whisper.py` - Transcription tests

## Templates
1. `templates/` directory - HTML templates

## Files to Exclude
1. All other `.bat` files (except the three essential ones)
2. All `.sh` files (for Windows compatibility)
3. Test reports and coverage files
4. Log files
5. Cache directories
6. Virtual environment
7. IDE-specific files
8. Temporary files
9. OS-specific files

## Directory Structure
```
zoom_poll_automator/
├── app.py
├── audio_capture.py
├── cli.py
├── config.py
├── poll_prompt.py
├── poller.py
├── README.md
├── requirements.txt
├── run.py
├── run_loop.py
├── run_tests.bat
├── setup.bat
├── start.bat
├── templates/
│   └── (template files)
├── tests/
│   ├── test_app_smoke.py
│   ├── test_audio_capture.py
│   ├── test_config.py
│   ├── test_integration.py
│   ├── test_performance.py
│   ├── test_poll_prompt.py
│   ├── test_poller.py
│   ├── test_security.py
│   └── test_transcribe_whisper.py
└── transcribe_whisper.py
```

## Notes
1. Make sure to include a proper `.env.example` file with template environment variables
2. Update the README.md with proper setup and usage instructions
3. Ensure all dependencies are listed in requirements.txt
4. Keep the test files organized and up to date
5. Maintain proper documentation for all major components 