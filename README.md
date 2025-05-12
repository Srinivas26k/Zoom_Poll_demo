# Zoom Poll Automator

An automated system that listens to Zoom meetings, transcribes the audio, and generates polls based on the conversation using AI.

## Features

- Real-time audio capture from Zoom meetings
- High-quality transcription using OpenAI's Whisper
- Intelligent poll generation using LLaMA 3.2
- Automatic poll posting to Zoom meetings
- Web interface for easy setup and monitoring
- Robust error handling and logging

## Prerequisites

- Python 3.8 or higher
- FFmpeg installed on your system
- Zoom API credentials (Client ID and Client Secret)
- Ollama running locally (for LLaMA 3.2)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Srinivas26k/zoom-poll-automator.git
cd zoom-poll-automator
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Unix or MacOS:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```env
# Zoom API Configuration
CLIENT_ID=your_zoom_client_id_here
CLIENT_SECRET=your_zoom_client_secret_here
REDIRECT_URI=http://localhost:8000/oauth/callback

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here  # Optional: Will be auto-generated if not provided
VERIFICATION_TOKEN=your_verification_token_here  # Optional: For webhook verification

# Ollama Configuration
LLAMA_HOST=http://localhost:11434  # Optional: Default Ollama host

# Logging Configuration
LOG_LEVEL=INFO  # Optional: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Usage

1. Start the web interface:
```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:8000`

3. Follow the setup wizard to:
   - Authorize with Zoom
   - Select your audio input device
   - Configure meeting settings

4. Start the automation:
   - Click "Start" to begin monitoring the meeting
   - The system will automatically:
     - Record audio segments
     - Transcribe the audio
     - Generate relevant polls
     - Post polls to the Zoom meeting

5. Monitor the process:
   - View real-time logs in the web interface
   - Check the status of each operation
   - View generated polls before they're posted

## Troubleshooting

### Common Issues

1. **No Audio Devices Found**
   - Ensure your microphone is properly connected
   - Check system audio settings
   - Try running `python audio_capture.py` to test audio devices

2. **Zoom API Authentication Failed**
   - Verify your CLIENT_ID and CLIENT_SECRET
   - Check if your Zoom app has the required permissions
   - Ensure your REDIRECT_URI matches your Zoom app settings

3. **Ollama Connection Issues**
   - Make sure Ollama is running (`ollama serve`)
   - Verify the LLAMA_HOST setting in your .env file
   - Check if you can access Ollama's API directly

### Logs

- Application logs are stored in `app.log`
- Check the web interface for real-time logs
- Use `LOG_LEVEL=DEBUG` in .env for detailed logging

## Development

### Project Structure

```
zoom-poll-automator/
├── app.py              # Web interface and main application
├── audio_capture.py    # Audio recording and processing
├── transcribe_whisper.py # Whisper transcription
├── poller.py          # Poll generation and posting
├── config.py          # Configuration management
├── run.py             # CLI entry point
├── requirements.txt   # Python dependencies
└── templates/         # Web interface templates
```

### Running Tests

```bash
python -m pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI Whisper for transcription
- LLaMA 3.2 for poll generation
- Zoom API for meeting integration
- Flask for the web interface