"""
core/speaker.py — Text-to-speech output layer
==============================================
Wraps pyttsx3 to provide a clean, thread-safe TTS interface.

    speaker.say("Hello world")          # Speaks and blocks until done
    speaker.say_async("Background msg") # Non-blocking
    speaker.play_activation_chime()     # Short audible feedback
"""

import threading
from typing import Optional

from core.logger import get_logger
from config import settings

logger = get_logger(__name__)


class Speaker:
    """
    Thread-safe text-to-speech wrapper around pyttsx3.

    pyttsx3 is not thread-safe, so all synthesis calls are serialised
    through a single dedicated worker thread.
    """

    def __init__(self, silent: bool = False):
        """
        Args:
            silent: If True, log speech but don't actually play audio.
                    Useful for testing or headless environments.
        """
        self._silent = silent
        self._engine = None
        self._lock = threading.Lock()

        if not silent:
            self._init_engine()

        logger.info(f"Speaker ready. Silent mode: {silent}")

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def say(self, text: str):
        """
        Speak `text` synchronously — blocks until the utterance finishes.

        Args:
            text: Plain text to synthesise.
        """
        if not text:
            return

        logger.info(f"[JARVIS] {text}")

        if self._silent:
            return

        self._speak(text)

    def say_async(self, text: str):
        """
        Speak `text` on a background thread — returns immediately.
        Note: overlapping calls will be queued behind each other.
        """
        t = threading.Thread(target=self.say, args=(text,), daemon=True)
        t.start()

    def play_activation_chime(self):
        """
        Short verbal acknowledgement played after the wake word is detected.
        Replace with an audio file playback for a real chime sound.
        """
        self.say("Yes?")

    def set_rate(self, rate: int):
        """Override speech rate at runtime (words per minute)."""
        if self._engine:
            self._engine.setProperty("rate", rate)

    def set_volume(self, volume: float):
        """Override volume at runtime (0.0–1.0)."""
        if self._engine:
            self._engine.setProperty("volume", max(0.0, min(1.0, volume)))

    def list_voices(self) -> list:
        """Return available voices from the current TTS engine."""
        if self._engine:
            return self._engine.getProperty("voices")
        return []

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _init_engine(self):
        """Initialise pyttsx3 and apply configured properties."""
        try:
            import pyttsx3  # type: ignore
            self._engine = pyttsx3.init()

            self._engine.setProperty("rate", settings.TTS_RATE)
            self._engine.setProperty("volume", settings.TTS_VOLUME)

            # Select voice by index
            voices = self._engine.getProperty("voices")
            if voices and settings.TTS_VOICE_INDEX < len(voices):
                self._engine.setProperty("voice", voices[settings.TTS_VOICE_INDEX].id)
                logger.debug(f"Using voice: {voices[settings.TTS_VOICE_INDEX].name}")

        except ImportError:
            logger.error("pyttsx3 not installed. Run: pip install pyttsx3")
            self._silent = True
        except Exception as exc:  # noqa: BLE001
            logger.error(f"TTS engine init failed: {exc}. Switching to silent mode.")
            self._silent = True

    def _speak(self, text: str):
        """Thread-safe synthesis call."""
        if self._engine is None:
            return

        with self._lock:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except RuntimeError as exc:
                # pyttsx3 can raise "run loop already started" in some envs
                logger.warning(f"TTS runtime error (non-fatal): {exc}")
            except Exception as exc:  # noqa: BLE001
                logger.error(f"TTS speak error: {exc}", exc_info=True)
