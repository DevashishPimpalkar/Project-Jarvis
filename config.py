"""
config.py — Centralised configuration for JARVIS
=================================================
All settings are read from environment variables (via .env) so that
secrets are never committed to source control.

Set up:
    1. Copy `.env.example` to `.env`
    2. Fill in your actual API keys
    3. Optionally override any default setting below
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


@dataclass
class Settings:
    # ------------------------------------------------------------------ #
    #  Wake word & timing                                                  #
    # ------------------------------------------------------------------ #
    WAKE_WORD: str              = os.getenv("WAKE_WORD", "jarvis")
    WAKE_WORD_TIMEOUT: float    = float(os.getenv("WAKE_WORD_TIMEOUT", "3"))   # seconds
    COMMAND_TIMEOUT: float      = float(os.getenv("COMMAND_TIMEOUT", "5"))     # seconds
    PHRASE_LIMIT: float         = float(os.getenv("PHRASE_LIMIT", "10"))       # max phrase length

    # ------------------------------------------------------------------ #
    #  Speech recognition                                                  #
    # ------------------------------------------------------------------ #
    # Engine: "google" (online) | "sphinx" (offline) | "whisper" (local AI)
    STT_ENGINE: str             = os.getenv("STT_ENGINE", "google")
    WHISPER_MODEL: str          = os.getenv("WHISPER_MODEL", "base")           # tiny/base/small/medium
    MIC_DEVICE_INDEX: Optional[int] = (
        int(os.getenv("MIC_DEVICE_INDEX")) if os.getenv("MIC_DEVICE_INDEX") else None
    )
    AMBIENT_NOISE_DURATION: float = float(os.getenv("AMBIENT_NOISE_DURATION", "1"))

    # ------------------------------------------------------------------ #
    #  Text-to-speech                                                      #
    # ------------------------------------------------------------------ #
    TTS_RATE: int               = int(os.getenv("TTS_RATE", "165"))            # words per minute
    TTS_VOLUME: float           = float(os.getenv("TTS_VOLUME", "0.9"))        # 0.0–1.0
    TTS_VOICE_INDEX: int        = int(os.getenv("TTS_VOICE_INDEX", "0"))       # 0=first system voice

    # ------------------------------------------------------------------ #
    #  Startup                                                             #
    # ------------------------------------------------------------------ #
    STARTUP_MESSAGE: str        = os.getenv(
        "STARTUP_MESSAGE",
        "All systems online. How can I help you?"
    )

    # ------------------------------------------------------------------ #
    #  NLP / Intent parsing                                                #
    # ------------------------------------------------------------------ #
    # Parser backend: "spacy" (local, fast) | "openai" | "grok"
    PARSER_BACKEND: str         = os.getenv("PARSER_BACKEND", "spacy")
    SPACY_MODEL: str            = os.getenv("SPACY_MODEL", "en_core_web_sm")

    # ------------------------------------------------------------------ #
    #  OpenAI                                                              #
    # ------------------------------------------------------------------ #
    OPENAI_API_KEY: str         = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str           = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_MAX_TOKENS: int      = int(os.getenv("OPENAI_MAX_TOKENS", "150"))

    # ------------------------------------------------------------------ #
    #  Grok (xAI)                                                          #
    # ------------------------------------------------------------------ #
    GROK_API_KEY: str           = os.getenv("GROK_API_KEY", "")
    GROK_BASE_URL: str          = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1")
    GROK_MODEL: str             = os.getenv("GROK_MODEL", "grok-beta")

    # ------------------------------------------------------------------ #
    #  Spotify                                                             #
    # ------------------------------------------------------------------ #
    SPOTIFY_CLIENT_ID: str      = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET: str  = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    SPOTIFY_REDIRECT_URI: str   = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
    SPOTIFY_SCOPE: str          = os.getenv(
        "SPOTIFY_SCOPE",
        "user-read-playback-state user-modify-playback-state user-read-currently-playing"
    )

    # ------------------------------------------------------------------ #
    #  Weather (OpenWeatherMap)                                            #
    # ------------------------------------------------------------------ #
    WEATHER_API_KEY: str        = os.getenv("WEATHER_API_KEY", "")
    DEFAULT_CITY: str           = os.getenv("DEFAULT_CITY", "New York")

    # ------------------------------------------------------------------ #
    #  Browser                                                             #
    # ------------------------------------------------------------------ #
    DEFAULT_BROWSER: str        = os.getenv("DEFAULT_BROWSER", "")  # empty = system default
    DEFAULT_SEARCH_ENGINE: str  = os.getenv("DEFAULT_SEARCH_ENGINE", "https://www.google.com/search?q=")

    # ------------------------------------------------------------------ #
    #  Logging                                                             #
    # ------------------------------------------------------------------ #
    LOG_LEVEL: str              = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str]     = os.getenv("LOG_FILE")               # None = stdout only

    # ------------------------------------------------------------------ #
    #  Handler registration                                                #
    # ------------------------------------------------------------------ #
    # Override to restrict which handlers are loaded (useful for testing)
    ENABLED_HANDLERS: list      = field(default_factory=lambda: [
        "spotify",
        "browser",
        "system",
        "weather",
    ])

    def validate(self) -> list[str]:
        """
        Return a list of warning messages for missing optional credentials.
        These are warnings only — JARVIS will still start, but some handlers
        may degrade gracefully.
        """
        warnings = []

        if self.PARSER_BACKEND == "openai" and not self.OPENAI_API_KEY:
            warnings.append("OPENAI_API_KEY not set; parser will fall back to spaCy.")

        if self.PARSER_BACKEND == "grok" and not self.GROK_API_KEY:
            warnings.append("GROK_API_KEY not set; parser will fall back to spaCy.")

        if "spotify" in self.ENABLED_HANDLERS:
            if not self.SPOTIFY_CLIENT_ID or not self.SPOTIFY_CLIENT_SECRET:
                warnings.append("Spotify credentials missing; SpotifyHandler will be disabled.")

        if "weather" in self.ENABLED_HANDLERS and not self.WEATHER_API_KEY:
            warnings.append("WEATHER_API_KEY not set; WeatherHandler will be disabled.")

        return warnings


# Singleton — import this everywhere
settings = Settings()
