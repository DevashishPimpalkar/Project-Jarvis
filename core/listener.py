"""
core/listener.py — Speech-to-text input layer
==============================================
Wraps SpeechRecognition to provide two public methods:

    listener.listen_for_wake_word(wake_word, timeout) → str | None
    listener.listen_for_command(timeout, phrase_limit) → str | None

Engine selection (via config.STT_ENGINE):
    "google"  — Free Google Web Speech API (requires internet)
    "sphinx"  — CMU Pocket Sphinx (offline, lower accuracy)
    "whisper" — OpenAI Whisper running locally (best offline quality)

If SpeechRecognition / PyAudio are not installed, the Listener raises
a clear ImportError with install instructions rather than crashing
silently or producing a confusing traceback.
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional

from config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# ------------------------------------------------------------------ #
#  Graceful dependency check                                           #
# ------------------------------------------------------------------ #

try:
    import speech_recognition as sr
    _SR_AVAILABLE = True
except ImportError:
    _SR_AVAILABLE = False
    sr = None  # type: ignore


def _require_sr():
    if not _SR_AVAILABLE:
        raise ImportError(
            "SpeechRecognition is not installed.\n"
            "Run:  pip install SpeechRecognition pyaudio\n"
            "macOS extra step:  brew install portaudio\n"
            "Linux extra step:  sudo apt install portaudio19-dev"
        )


class Listener:
    """
    Microphone listener that exposes a clean API for the main event loop.
    All SpeechRecognition internals are encapsulated here.
    """

    def __init__(self):
        _require_sr()
        self._recognizer = sr.Recognizer()
        self._mic = self._build_microphone()
        self._calibrate()
        self._whisper_model = None
        logger.info(f"Listener ready. STT engine: {settings.STT_ENGINE}")

    # ------------------------------------------------------------------ #
    #  Setup                                                               #
    # ------------------------------------------------------------------ #

    def _build_microphone(self) -> "sr.Microphone":
        idx = settings.MIC_DEVICE_INDEX
        if idx is not None:
            logger.debug(f"Using microphone device index {idx}")
            return sr.Microphone(device_index=idx)
        return sr.Microphone()

    def _calibrate(self):
        """Adjust for ambient noise so the recogniser isn't over-sensitive."""
        logger.debug("Calibrating for ambient noise…")
        try:
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(
                    source, duration=settings.AMBIENT_NOISE_DURATION
                )
            logger.debug("Ambient noise calibration complete.")
        except OSError as exc:
            logger.warning(
                f"Could not access microphone during calibration: {exc}\n"
                "Check that a microphone is connected. "
                "List devices with:  python -c \"import speech_recognition as sr; "
                "print(sr.Microphone.list_microphone_names())\""
            )

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def listen_for_wake_word(
        self,
        wake_word: str = "jarvis",
        timeout: float = 3.0,
    ) -> Optional[str]:
        """
        Capture a brief snippet and return it if the wake word is present.

        Returns:
            Transcribed text if wake word found, else None.
        """
        audio = self._capture_audio(timeout=timeout, phrase_limit=4)
        if audio is None:
            return None
        text = self._transcribe(audio)
        if text and wake_word.lower() in text.lower():
            return text
        return None

    def listen_for_command(
        self,
        timeout: float = 5.0,
        phrase_limit: float = 10.0,
    ) -> Optional[str]:
        """
        Listen for a full command utterance.

        Returns:
            Transcribed command text, or None if nothing was recognised.
        """
        audio = self._capture_audio(timeout=timeout, phrase_limit=phrase_limit)
        if audio is None:
            return None
        return self._transcribe(audio)

    @staticmethod
    def list_microphones() -> list[str]:
        """Return available microphone device names."""
        _require_sr()
        return sr.Microphone.list_microphone_names()

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _capture_audio(
        self,
        timeout: float,
        phrase_limit: float,
    ) -> Optional["sr.AudioData"]:
        try:
            with self._mic as source:
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit,
                )
            return audio
        except sr.WaitTimeoutError:
            logger.debug("Mic timeout — no speech detected.")
            return None
        except OSError as exc:
            logger.error(
                f"Microphone hardware error: {exc}\n"
                "Try setting MIC_DEVICE_INDEX in .env. "
                "Run python -c \"import speech_recognition as sr; "
                "print(sr.Microphone.list_microphone_names())\" to list devices."
            )
            return None

    def _transcribe(self, audio: "sr.AudioData") -> Optional[str]:
        """Send AudioData through the configured STT engine."""
        engine = settings.STT_ENGINE.lower()
        try:
            if engine == "google":
                return self._transcribe_google(audio)
            elif engine == "sphinx":
                return self._transcribe_sphinx(audio)
            elif engine == "whisper":
                return self._transcribe_whisper(audio)
            else:
                logger.warning(f"Unknown STT engine '{engine}'. Falling back to Google.")
                return self._transcribe_google(audio)
        except sr.UnknownValueError:
            logger.debug("Speech not understood.")
            return None
        except sr.RequestError as exc:
            logger.error(f"STT API request failed: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Unexpected transcription error: {exc}", exc_info=True)
            return None

    def _transcribe_google(self, audio: "sr.AudioData") -> str:
        return self._recognizer.recognize_google(audio)

    def _transcribe_sphinx(self, audio: "sr.AudioData") -> str:
        try:
            return self._recognizer.recognize_sphinx(audio)
        except sr.RequestError:
            logger.warning(
                "Sphinx not available. Install with: pip install pocketsphinx"
            )
            raise

    def _transcribe_whisper(self, audio: "sr.AudioData") -> str:
        """Use OpenAI Whisper locally. Requires: pip install openai-whisper torch"""
        if self._whisper_model is None:
            try:
                import whisper  # type: ignore
            except ImportError:
                raise ImportError(
                    "Whisper not installed.\n"
                    "Run: pip install openai-whisper torch"
                )
            logger.info(f"Loading Whisper model '{settings.WHISPER_MODEL}'…")
            self._whisper_model = whisper.load_model(settings.WHISPER_MODEL)

        wav_data = audio.get_wav_data()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_data)
            tmp_path = tmp.name
        try:
            result = self._whisper_model.transcribe(tmp_path)
            return result["text"].strip()
        finally:
            os.unlink(tmp_path)
