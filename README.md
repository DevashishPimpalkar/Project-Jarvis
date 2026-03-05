# 🤖 JARVIS — Voice-Activated AI Assistant

A production-ready, modular voice assistant that runs **entirely on your local machine**. Say "Hey Jarvis" to activate, speak a command, and let JARVIS handle the rest.

```
┌─────────────────────────────────────────────────────────┐
│  🎙  Wake word detected                                  │
│  📝  "Play Bohemian Rhapsody by Queen on Spotify"        │
│  🔍  Intent: play_song → SpotifyHandler                  │
│  🎵  "Playing Bohemian Rhapsody by Queen."               │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Capability | Detail |
|---|---|
| **Wake word** | Always-on listening; activates on "Hey Jarvis" |
| **Push-to-talk** | Press Enter instead of wake word |
| **Spotify control** | Play, pause, skip, volume, now playing |
| **Web navigation** | Open URLs, Google Search, YouTube |
| **System commands** | Time, date, timers, app launcher |
| **Weather** | Current conditions via OpenWeatherMap |
| **Offline-first** | spaCy NLU runs 100% locally; Google STT optional |
| **AI parsing** | OpenAI / Grok fallback for ambiguous commands |
| **Extensible** | Add a new handler in ~20 lines, zero core changes |

---

## 📋 Prerequisites

- Python 3.10 or higher
- A working microphone
- Speakers or headphones

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/jarvis.git
cd jarvis
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **macOS / Linux — PyAudio**: if `pip install pyaudio` fails, first install PortAudio:
> ```bash
> brew install portaudio          # macOS
> sudo apt install portaudio19-dev # Ubuntu/Debian
> ```

### 4. Download the spaCy language model

```bash
python -m spacy download en_core_web_sm
```

### 5. Configure your credentials

```bash
cp .env.example .env
```

Open `.env` and fill in the API keys you need (see [Configuration](#-configuration) below). All keys are optional except for features you want to use.

### 6. Run JARVIS

```bash
# Wake-word mode (say "Hey Jarvis" to activate)
python main.py

# Push-to-talk mode (press Enter to speak)
python main.py --push-to-talk

# Text-only output (no TTS, useful for debugging)
python main.py --no-voice

# Debug logging
python main.py --debug
```

---

## 🗣️ Supported Commands

### 🎵 Spotify

| Say… | What happens |
|---|---|
| "Play Blinding Lights by The Weeknd" | Searches and plays on Spotify |
| "Play my Discover Weekly playlist" | Plays a playlist |
| "Pause the music" | Pauses playback |
| "Resume" | Resumes playback |
| "Skip this track" | Skips to the next song |
| "Volume up / Volume down" | Adjusts by 10% |
| "What's currently playing?" | Announces track and artist |

### 🌐 Browser

| Say… | What happens |
|---|---|
| "Search for Python tutorials" | Google search |
| "Open github.com" | Navigates to the URL |
| "Open YouTube" | Opens YouTube homepage |
| "Play Never Gonna Give You Up on YouTube" | Searches YouTube |

### 🖥️ System

| Say… | What happens |
|---|---|
| "What time is it?" | Announces current time |
| "What's today's date?" | Announces the date |
| "Set a timer for 5 minutes" | Countdown with voice alert |
| "Open VS Code" | Launches the application |
| "Goodbye" / "Shutdown" | Gracefully exits JARVIS |

### 🌤️ Weather

| Say… | What happens |
|---|---|
| "What's the weather?" | Current conditions for DEFAULT_CITY |
| "Weather in Tokyo" | Current conditions for Tokyo |

---

## ⚙️ Configuration

All settings live in `.env` (copy from `.env.example`).

### Minimum viable setup (offline, no API keys)

```env
STT_ENGINE=google          # uses free Google Web Speech (internet required)
PARSER_BACKEND=spacy       # fully offline NLU
```

### Enable Spotify

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new application
3. Set Redirect URI to `http://localhost:8888/callback`
4. Copy Client ID and Client Secret to `.env`:

```env
SPOTIFY_CLIENT_ID=your_id
SPOTIFY_CLIENT_SECRET=your_secret
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
```

First launch will open a browser tab for OAuth authorisation.

### Enable AI command parsing (OpenAI)

```env
PARSER_BACKEND=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### Enable AI command parsing (Grok)

```env
PARSER_BACKEND=grok
GROK_API_KEY=xai-...
```

### Enable Weather

1. Get a free API key at [openweathermap.org](https://openweathermap.org/api)
2. Add to `.env`:

```env
WEATHER_API_KEY=your_key
DEFAULT_CITY=London
```

### Fully offline mode (Whisper STT)

```bash
pip install openai-whisper torch
```

```env
STT_ENGINE=whisper
WHISPER_MODEL=base       # tiny / base / small / medium / large
PARSER_BACKEND=spacy
```

---

## 🏗️ Project Structure

```
jarvis/
├── main.py                    # Event loop, JARVIS orchestrator
├── config.py                  # All settings from .env
├── requirements.txt
├── .env.example               # Copy to .env and fill in
│
├── core/
│   ├── listener.py            # Microphone → text (SpeechRecognition)
│   ├── speaker.py             # Text → speech (pyttsx3)
│   ├── parser.py              # Text → Intent (spaCy / OpenAI / Grok)
│   ├── dispatcher.py          # Intent → Handler (auto-discovery)
│   └── logger.py              # Centralised logging
│
├── handlers/
│   ├── base_handler.py        # Abstract base class (extend this)
│   ├── spotify_handler.py     # Spotify playback control
│   ├── browser_handler.py     # Web navigation and search
│   ├── system_handler.py      # Time, date, timer, app launch
│   ├── weather_handler.py     # Current weather conditions
│   └── example_custom_handler.py  # Template for new handlers
│
└── utils/
    └── helpers.py             # Shared utility functions
```

---

## 🔌 Adding a New Command (Handler Guide)

Adding a new voice command takes about 5 minutes:

### Step 1 — Copy the template

```bash
cp handlers/example_custom_handler.py handlers/joke_handler.py
```

### Step 2 — Implement the handler

```python
# handlers/joke_handler.py
import requests
from handlers.base_handler import BaseHandler
from core.parser import Intent

class JokeHandler(BaseHandler):

    def supported_intents(self):
        return [("tell_joke", "")]       # matches "tell_joke" regardless of target

    def is_available(self):
        try:
            import requests
            return True
        except ImportError:
            return False

    def handle(self, intent: Intent):
        resp = requests.get("https://official-joke-api.appspot.com/random_joke").json()
        self.speak(f"{resp['setup']} … {resp['punchline']}")
```

### Step 3 — Register the new intent (optional, for rule-based matching)

In `core/parser.py`, add to `INTENT_CATALOGUE`:

```python
"tell_joke": {"target": "", "description": "Tell a random joke"},
```

And add a pattern in `_rule_based_parse()`:

```python
if re.search(r"\b(tell|say|give me).*\bjoke\b", text):
    return Intent("tell_joke", "", raw_text=text)
```

### Step 4 — Restart JARVIS

That's it. The Dispatcher auto-discovers the new handler.

---

## 🐛 Troubleshooting

**"No module named 'pyaudio'"**
```bash
# macOS
brew install portaudio && pip install pyaudio

# Ubuntu/Debian
sudo apt install portaudio19-dev python3-pyaudio
```

**Microphone not detected / wrong device**
```python
# Run this snippet to list devices:
import speech_recognition as sr
print(sr.Microphone.list_microphone_names())
```
Then set `MIC_DEVICE_INDEX=N` in `.env`.

**Spotify "No active device found"**
Make sure Spotify is open and playing something on at least one device before issuing commands.

**spaCy model not found**
```bash
python -m spacy download en_core_web_sm
```

**pyttsx3 fails on Linux**
```bash
sudo apt install espeak libespeak-dev
```

---

## 📄 License

MIT — do whatever you like with it.
