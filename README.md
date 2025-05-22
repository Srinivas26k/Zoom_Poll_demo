
# 🚀 Zoom Poll Automator

> 🎙️ Transforming Online Meetings with AI-Powered Engagement

Zoom Poll Automator is an intelligent system that revolutionizes online meetings by generating contextual polls in real-time, keeping participants engaged and discussions dynamic.

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python Version](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Architecture](https://github.com/Srinivas26k/Zoom_Poll_demo/blob/main/assets/diagram%20(1).png)

---

## 🌟 Key Features

- 🎧 **Real-time Audio Capture** – Listens to Zoom meetings seamlessly  
- 🧠 **Advanced Transcription** – Uses OpenAI Whisper for accurate transcription  
- 🗳️ **Intelligent Poll Generation** – Powered by LLaMA 3.2 for relevant, on-topic polls  
- 🔄 **Automatic Zoom Integration** – Posts polls directly into your meeting  
- 📝 **AI Meeting Notes** – Automatically generates summaries and action items
- 🎙️ **Internal Recording** – Captures both speaker and microphone audio for comprehensive recording
- 🔍 **Live Transcription** – Shows real-time meeting transcript with speaker identification
- 🌐 **Web Interface** – Friendly setup wizard and live status  
- 🛠️ **Robust Error Handling** – Secure logs and fallback strategies  

---

## 🎯 Who Is This For?

- 📊 Meeting Hosts seeking engagement  
- 👥 Team Managers needing quick feedback  
- 🏫 Educators making classes interactive  
- 🎤 Conference Organizers improving audience participation  

---

## 🛠 Prerequisites

- Python 3.8+
- FFmpeg (for audio processing)
- Zoom API credentials (Client ID, Secret)
- OpenAI API Key (for transcription)
- Ollama (for LLaMA 3.2 - used for poll generation)
- Virtual Audio Cable software
  - Windows: [VB-Audio Virtual Cable](https://vb-audio.com/Cable/)
  - macOS: [BlackHole](https://existential.audio/blackhole/)
  - Linux: Configure PulseAudio with module-loopback

---

## 💻 Installation

The primary way to install and set up the Zoom Poll Automator is via the interactive menu system.

```bash
# 1. Clone the repository
git clone https://github.com/Srinivas26k/zoom-poll-automator.git
cd zoom-poll-automator

# 2. Run the interactive setup menu
# This script will guide you through creating a virtual environment,
# installing dependencies, and configuring necessary credentials.
python menu.py 

# 3. In the menu, select "First Time Setup".
```

The setup process handled by `menu.py` (which utilizes `setup.py`) will:
- Create a Python virtual environment (`venv` folder).
- Activate the virtual environment.
- Install all required Python packages from `requirements.txt`.
- Guide you through creating and populating a `.env` file with necessary credentials.

### `.env` File Configuration

The setup wizard will prompt you for the following information, which will be stored in a `.env` file in the project root:
(This is for your reference; the setup wizard will guide you through this.)
```env
# OAuth credentials (from your Zoom App)
# You need to register a Zoom App in the Zoom Developer Portal at https://marketplace.zoom.us/
CLIENT_ID=
CLIENT_SECRET=
# Redirect URI (must match exactly in Zoom App settings)
REDIRECT_URI=http://localhost:8000/oauth/callback
# Webhook verification tokens (for future use)
SECRET_TOKEN=
VERIFICATION_TOKEN=C
# Ollama host (LLaMA)
LLAMA_HOST=http://localhost:11434
# Flask Secret Key for session management
# Generate a strong random key (e.g., using python -c "import os; print(os.urandom(24).hex())")
FLASK_SECRET_KEY=

```

---

## 🚀 Usage

The recommended way to use the application is through the interactive menu system.

**1. Using the Menu System (Recommended):**

   Run the menu:
   ```bash
   python menu.py
   ```
   - **First Time Setup**: If you haven't already, choose option `1` to configure the application.
   - **Run Automation (Web UI)**: Choose option `2` to start the Flask web server. You can then access the application at `http://localhost:8000`.
   - **Update Configuration**: Choose option `3` to update your `.env` file credentials.

**2. Direct Web Interface Launch (After Setup):**

   If you have already completed the first-time setup via `menu.py`, you can directly start the web application:
   ```bash
   # Ensure your virtual environment is activated
   # Windows: venv\Scripts\activate
   # macOS/Linux: source venv/bin/activate
   
   python app.py
   ```
   Then, visit `http://localhost:8000` in your web browser.

**3. Recording and Analysis Interface:**

   Once the web application is running, navigate to `http://localhost:8000/recorder`:
   1. Select your audio device (virtual audio devices are recommended for capturing all meeting audio).
   2. Click "Start Recording" to begin.
   3. View real-time transcription, AI-generated notes, and suggested polls on the page.
   4. Click "Stop Recording" when your meeting ends.
   5. Download options for transcripts, notes, and polls will be available.

**4. Virtual Audio Setup (Recommended for full audio capture):**

   To capture all audio from a Zoom meeting (including remote participants), you'll need a virtual audio device:
   - **Windows**: Install [VB-Audio Virtual Cable](https://vb-audio.com/Cable/). Set Zoom's speaker output to "CABLE Input" and select "CABLE Output" as the recording device in this application.
   - **macOS**: Install [BlackHole](https://existential.audio/blackhole/). Configure a Multi-Output Device to send system audio to BlackHole and your headphones. Select BlackHole as the recording device.
   - **Linux**: Configure PulseAudio using `module-loopback` or use a tool like `pavucontrol` to route application audio.

**5. Command-Line Interface (CLI) Options:**

   - **`start.bat` (Windows):**
     A simple script for Windows users to quickly launch the interactive menu (`python menu.py`). This is ideal for non-technical users.

   - **`python run.py`:**
     This script runs a continuous automation cycle using the default system audio device (or the one configured if `MeetingRecorder` is modified to accept a device name directly via `run.py`). It uses environment variables for Zoom token and meeting ID.
     - `python run.py`: Starts continuous automation.
     - `python run.py --test`: Runs a single cycle for testing purposes.
     - *Note*: The `--duration` argument for `run.py` is currently a no-op as the recording segment duration is managed internally by `MeetingRecorder`.

---

## 🧪 Test Insights

### ✅ Test Results Summary

- **Total Tests**: 29  
- **Passed**: 29 
- **Failed**: 0 
- **Duration**: (Will be updated after tests run)

#### ✔️ Top Passed Tests
- `test_transcription_speed`
- `test_generate_poll_success`
- `test_complete_workflow`
- `test_env_file_not_committed`
- `test_poll_generation_performance`

📊 **Performance Benchmark**
![Performance Chart](https://github.com/Srinivas26k/Zoom_Poll_demo/blob/main/assets/test_pass_pie_chart.png)

📈 **Test Pass Rate**
![Pass Rate](https://github.com/Srinivas26k/Zoom_Poll_demo/blob/main/assets/performance_chart.png)

---

## 🌐 Supported Platforms

| OS         | Status        |
|------------|---------------|
| Windows    | ✅ Supported  |
| macOS      | ✅ Supported  |
| Linux      | ✅ Supported  |

---

## 📂 Project Structure

```
zoom-poll-automator/
├── app.py                   # Main Flask web application
├── menu.py                  # Main interactive menu for setup and application launching
├── meeting_recorder.py      # Core class for managing meeting recording, transcription, and analysis
├── run_loop.py              # Core recording/transcription loop logic used by app.py/run.py
├── run.py                   # CLI entry point for direct automation
├── audio_capture.py         # Audio device utility functions
├── transcribe_whisper.py    # Handles audio transcription using Whisper
├── ai_notes.py              # AI-powered note and summary generation
├── poll_prompt.py           # Defines prompts for LLM-based poll generation
├── poller.py                # Generates polls from transcripts and posts to Zoom
├── virtual_audio.py         # Utilities for virtual audio device setup (conceptual)
├── config.py                # Handles application configuration and .env loading
├── setup.py                 # Core setup logic (venv, dependencies, .env) called by menu.py
├── start.bat                # Windows quick launch (runs python menu.py)
├── start.sh                 # macOS/Linux quick launch (runs python menu.py)
├── setup.bat                # Simplified Windows script, points to menu.py
├── setup.sh                 # Simplified macOS/Linux script, points to menu.py
├── requirements.txt         # Python package dependencies
├── .env.example             # Example environment file
├── static/                  # Static assets (CSS, JS, images) for web UI
├── templates/               # HTML templates for web UI
└── tests/                   # Unit, integration, and other tests
```

---

## 🧠 Troubleshooting

- **No Audio Device?** – Ensure microphone access is granted to your terminal/Python. You can list available devices by running `python audio_capture.py` (if its `if __name__ == "__main__":` block is enabled for listing) or check within the application's web UI if available.
- **Zoom API Failing?** – Double-check your `CLIENT_ID`, `CLIENT_SECRET`, and `REDIRECT_URI` in the `.env` file. Ensure the `REDIRECT_URI` matches exactly what's in your Zoom App Marketplace settings.
- **Ollama Issues?** – Make sure the Ollama application is running and the specified model (e.g., `llama3.2`) is pulled (`ollama pull llama3.2`). The application expects Ollama to be accessible at the `LLAMA_HOST` defined in your `.env` file (default: `http://localhost:11434`).
- **Virtual Environment Not Activating?** – If `python menu.py` fails, try manually creating and activating the virtual environment:
  ```bash
  python -m venv venv
  # Windows:
  venv\Scripts\activate
  # macOS/Linux:
  source venv/bin/activate
  # Then run:
  pip install -r requirements.txt 
  python menu.py 
  ```

---

## 🔐 Security

- OAuth 2.0 with secure token handling  
- No storage of meeting content  
- `.env` protected and checked in CI  

---

## 📋 Roadmap

- [X] macOS/Linux support (Basic CLI and setup scripts provided)
- [ ] Enhanced Web UI for live meeting management
- [ ] Analytics dashboard for poll results and engagement
- [ ] More sophisticated AI integrations for nuanced poll suggestions
- [ ] Voice sentiment-based poll timing

---

## 🙌 Acknowledgments

- OpenAI Whisper
- LLaMA 3.2
- Flask
- Zoom API

---

**Version**: 1.0.0  
**Last Updated**: May 2025

**Happy Engaging Meetings!** 🎉  
