
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
- FFmpeg
- Zoom API credentials (Client ID, Secret)
- OpenAI API Key
- Ollama (for LLaMA 3.2)

---

## 💻 Installation

```bash
# Clone
git clone https://github.com/Srinivas26k/zoom-poll-automator.git
cd zoom-poll-automator

# Virtual Environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt
```

Create a `.env` file and add:
```env
CLIENT_ID=your_zoom_client_id
CLIENT_SECRET=your_zoom_client_secret
REDIRECT_URI=http://localhost:8000/oauth/callback
OPENAI_API_KEY=your_openai_key
```

---

## 🚀 Usage

### Web Interface

```bash
python app.py
# Visit http://localhost:8000 and follow setup wizard
```

### CLI

```bash
python run.py         # Continuous automation
python run.py --test  # Single test cycle
start.bat             # Windows quick launch
```

---

## 🧪 Test Insights

### ✅ Test Results Summary

- **Total Tests**: 29  
- **Passed**: 23  
- **Duration**: 39.98 seconds

#### ✔️ Top Passed Tests
- `test_transcription_speed`
- `test_generate_poll_success`
- `test_complete_workflow`
- `test_env_file_not_committed`
- `test_poll_generation_performance`

📊 **Performance Benchmark**
![Performance Chart](test_pass_pie_chart.png)

📈 **Test Pass Rate**
![Pass Rate](performance_chart.png)

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
├── app.py
├── audio_capture.py
├── transcribe_whisper.py
├── poller.py
├── config.py
├── run.py
├── setup.bat / setup.sh
├── start.bat / start.sh
├── templates/
├── tests/
└── requirements.txt
```

---

## 🧠 Troubleshooting

- **No Audio Device?** – Ensure mic access + test with `python audio_capture.py`
- **Zoom API Failing?** – Check client credentials and callback URLs
- **Ollama Issues?** – Make sure it’s running: `ollama serve`

---

## 🔐 Security

- OAuth 2.0 with secure token handling  
- No storage of meeting content  
- `.env` protected and checked in CI  

---

## 📋 Roadmap

- [ ] macOS/Linux support
- [ ] Analytics dashboard
- [ ] Enhanced AI integrations
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
