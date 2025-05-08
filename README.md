# Zoom Poll Automator

## Overview

The Zoom Poll Automator is a tool that automatically generates and posts polls to Zoom meetings based on meeting audio. It works by:

1. **Capturing meeting audio** from your system
2. **Transcribing the audio** using Whisper AI
3. **Generating relevant polls** using LLaMA 3.2
4. **Posting the polls** to your active Zoom meeting

This creates an interactive and engaging meeting experience with minimal effort.

## Quick Start

### Installation

1. Download the repository
2. Open a terminal in the repository directory
3. Run the setup command:
   ```bash
   python zoom-poll setup
   ```
4. Follow the guided setup process
5. Start the application:
   ```bash
   python zoom-poll start
   ```

## Requirements

- **Python 3.8+** - For the core application
- **Ollama** - For running the LLaMA 3.2 model
- **Zoom Developer Account** - To create a Zoom App for API access
- **Audio Capture Device** - Like "Stereo Mix" on Windows

## Commands

The Zoom Poll Automator provides several commands:

### Setup
```bash
python zoom-poll setup
```
Initial setup of the application, including:
- Creating virtual environment
- Installing dependencies
- Configuring Zoom OAuth credentials
- Setting up Ollama

### Start
```bash
python zoom-poll start
```
Starts the Zoom Poll Automator web interface.

### Status
```bash
python zoom-poll status
```
Shows the current status of the application, including:
- Python environment
- Ollama status
- Configuration status

## Detailed Setup Instructions

### 1. Install Prerequisites

#### Python
- Download and install Python 3.8 or higher from [python.org](https://www.python.org/downloads/)
- Ensure Python is added to your PATH during installation

#### Ollama
- Download and install Ollama from [ollama.ai](https://ollama.ai/download)
- After installation, run in terminal/command prompt: `ollama serve`

### 2. Create a Zoom OAuth App

1. Go to [Zoom Developer Portal](https://marketplace.zoom.us/develop/create)
2. Click "Create" and select "OAuth" app type
3. Fill in the app information (name, description, etc.)
4. Add the following scopes:
   - `meeting:read:meeting_transcript`
   - `meeting:read:list_meetings` 
   - `meeting:read:poll`
   - `meeting:read:token` 
   - `meeting:write:poll`
   - `meeting:update:poll` 
   - `user:read:zak`
   - `zoomapp:inmeeting`
5. Set the Redirect URL to: `http://localhost:8000/oauth/callback`
6. Note your Client ID and Client Secret (you'll need these during setup)

### 3. Configure Audio Capture

For the automation to work, you need to route your meeting audio to a recording device:

#### Windows
- Enable "Stereo Mix" in Sound settings
- Right-click the speaker icon → Sound settings → Input → Enable Stereo Mix

#### macOS
- Install a virtual audio device like [BlackHole](https://github.com/ExistentialAudio/BlackHole)
- Configure audio routing to capture meeting audio

## Using the Application

### First-Time Setup

1. Run `python zoom-poll setup`
2. Follow the prompts to:
   - Install dependencies
   - Configure Zoom credentials
   - Set up Ollama
3. The setup process will guide you through all necessary steps

### Regular Usage

1. Run `python zoom-poll start`
2. Access the web interface at http://localhost:8000
3. Connect to Zoom if needed
4. Enter your meeting ID
5. Set the recording duration
6. Select your audio device
7. Click "Start Automation"

## Troubleshooting

### Audio Not Working
- Ensure your audio device is properly configured
- Check that meeting audio is routing to your selected input device
- Try a different audio device if available

### Ollama Connection Issues
- Make sure Ollama is running (`ollama serve` in a separate terminal)
- Verify that the LLaMA 3.2 model is installed (`ollama list`)
- Check your network connection if using a remote Ollama server

### Zoom API Errors
- Verify your Client ID and Client Secret are correct
- Make sure your OAuth app has all required scopes
- Check if your Zoom token has expired (re-authenticate if needed)

## Advanced Configuration

The `.env` file stores your configuration:

```
CLIENT_ID=your_zoom_client_id
CLIENT_SECRET=your_zoom_client_secret
REDIRECT_URI=http://localhost:8000/oauth/callback
SECRET_TOKEN=random_secret_key
LLAMA_HOST=http://localhost:11434
```

You can edit this file to:
- Change the Ollama server address
- Update your Zoom API credentials
- Modify the redirect URI if needed

## Technical Details

- **Flask**: Web interface and OAuth handling
- **Whisper**: OpenAI's speech-to-text AI (tiny.en model)
- **LLaMA 3.2**: Open-source LLM for generating contextual polls
- **sounddevice/soundfile**: Audio capture and processing
- **Click**: Command-line interface
- **Rich**: Terminal formatting and progress bars

## License

[Add your license information here]

---

*Developed by [Your Name/Organization]*