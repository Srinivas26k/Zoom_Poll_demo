# 🚀 Zoom Poll Automator

## Transforming Online Meetings with AI-Powered Engagement

Zoom Poll Automator is an intelligent system that revolutionizes online meetings by generating contextual polls in real-time, keeping participants engaged and discussions dynamic.

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python Version](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Architecture](https://github.com/Srinivas26k/Zoom_Poll_demo/blob/main/assets/diagram%20(1).png)
### 🌟 Key Features

- **Real-time Audio Capture**: Listens to Zoom meetings seamlessly
- **Advanced Transcription**: Uses OpenAI's Whisper for high-accuracy transcription
- **Intelligent Poll Generation**: Leverages LLaMA 3.2 to create contextually relevant polls
- **Automatic Zoom Integration**: Posts polls directly in your meeting
- **User-Friendly Web Interface**: Easy setup and monitoring
- **Robust Error Handling**: Comprehensive logging and error management

### 🎯 Who Is This For?

- 📊 Meeting Hosts seeking higher participant engagement
- 👥 Team Managers wanting instant feedback
- 🏫 Educators making online classes interactive
- 🎤 Conference Organizers looking for dynamic audience interaction

## 🛠 Prerequisites

- **Python**: 3.8 or higher
- **FFmpeg**: Multimedia framework
- **Zoom API Credentials**: Client ID and Client Secret
- **Ollama**: Local AI model hosting

## 💻 Installation

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/Srinivas26k/zoom-poll-automator.git
   cd zoom-poll-automator
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Create a `.env` file in the project root
   - Add your Zoom API credentials:
     ```
     CLIENT_ID=your_zoom_client_id
     CLIENT_SECRET=your_zoom_client_secret
     REDIRECT_URI=http://localhost:8000/oauth/callback
     ```

## 🚀 Usage

### Web Interface

1. Start the application:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to `http://localhost:8000`

3. Follow the setup wizard to:
   - Authorize with Zoom
   - Select audio input device
   - Configure meeting settings

### CLI Automation

```bash
# Run a single test cycle
python run.py --test

# Run continuous automation
python run.py
```
```
#double click the
start.bat #only for windows 
```

## 🛡 Platform Support

- ✅ Windows 10/11 (64-bit)
- 🟨 macOS (Coming Soon)
- 🟨 Linux (Coming Soon)

## 🧪 Running Tests

```bash
python -m pytest tests/
```

## 🔍 Troubleshooting

### Common Issues

1. **No Audio Devices Found**
   - Ensure microphone is connected
   - Check system audio settings
   - Test audio capture with `python audio_capture.py`

2. **Zoom API Authentication Failed**
   - Verify CLIENT_ID and CLIENT_SECRET
   - Check Zoom app permissions
   - Confirm REDIRECT_URI matches Zoom app settings

3. **Ollama Connection Issues**
   - Ensure Ollama is running (`ollama serve`)
   - Verify LLAMA_HOST in .env file
   - Check Ollama API accessibility

## 📂 Project Structure

```
zoom-poll-automator/
├── app.py              # Web interface and main application
├── audio_capture.py    # Audio recording and processing
├── transcribe_whisper.py # Whisper transcription
├── poller.py           # Poll generation and posting
├── config.py           # Configuration management
├── run.py              # CLI entry point
├── requirements.txt    # Python dependencies
├── setup.bat/setup.sh  # Setup scripts
├── start.bat/start.sh  # Start scripts
├── tests/              # Pytest test suite
└── templates/          # Web interface templates
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📋 Roadmap

- [ ] macOS Support
- [ ] Linux Installation Scripts
- [ ] Enhanced AI Models
- [ ] Multi-Platform Meeting Support
- [ ] Advanced Analytics Dashboard

## 🔐 Security

- OAuth 2.0 Authentication
- Secure Token Management
- Minimal Data Retention
- No Permanent Storage of Meeting Conversations

## 📄 License

Distributed under the MIT License. See `LICENSE` file for details.

## 🌐 Community & Support

- **GitHub Discussions**: Ask questions, share experiences
- **Issue Tracker**: Report bugs, suggest features


## 🙌 Acknowledgments

- OpenAI Whisper
- LLaMA 3.2
- Zoom API
- Flask

---

**Version**: 1.0.0
**Last Updated**: May 2024

**Happy Engaging Meetings!** 🎉
