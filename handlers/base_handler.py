"""
handlers/base_handler.py — Abstract base class for all JARVIS handlers
=======================================================================
Every handler MUST subclass BaseHandler and implement:

    supported_intents()  → list of (action, target) tuples this handles
    handle(intent)       → execute the command and give voice feedback
    is_available()       → True if required deps/credentials are present

The Dispatcher auto-discovers and instantiates all concrete subclasses
found in the `handlers/` package — no manual registration required.

Example minimal handler
-----------------------
    from handlers.base_handler import BaseHandler
    from core.parser import Intent

    class HelloHandler(BaseHandler):
        def supported_intents(self):
            return [("say_hello", "")]

        def handle(self, intent: Intent):
            name = intent.params.get("name", "world")
            self.speak(f"Hello, {name}!")

        def is_available(self):
            return True
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.logger import get_logger
from core.parser import Intent


class BaseHandler(ABC):
    """
    Abstract base for all command handlers.

    Subclass this, implement the three abstract methods, and drop the
    file in the `handlers/` directory — the Dispatcher does the rest.
    """

    def __init__(self, speaker=None):
        """
        Args:
            speaker: Speaker instance for TTS responses.
                     May be None in test contexts.
        """
        self._speaker = speaker
        self.logger = get_logger(self.__class__.__name__)

    # ------------------------------------------------------------------ #
    #  Abstract interface — must be implemented by every handler           #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def supported_intents(self) -> list[tuple[str, str]]:
        """
        Declare which (action, target) pairs this handler processes.

        Return a list of 2-tuples.  Use "" as target to match any target
        for that action.

        Example:
            return [
                ("play_song", "spotify"),
                ("pause_music", "spotify"),
            ]
        """
        ...

    @abstractmethod
    def handle(self, intent: Intent) -> None:
        """
        Execute the command described by `intent`.

        - Read parameters from `intent.params`.
        - Call `self.speak(text)` to give voice feedback.
        - Raise exceptions freely — the Dispatcher catches them.

        Args:
            intent: Fully populated Intent from the parser.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """
        Return True if this handler's prerequisites are met.

        Check for required packages, API keys, etc. here.
        The Dispatcher calls this during discovery and skips the handler
        if it returns False, logging a friendly warning.
        """
        ...

    # ------------------------------------------------------------------ #
    #  Convenience helpers available to all handlers                      #
    # ------------------------------------------------------------------ #

    def speak(self, text: str) -> None:
        """
        Send a spoken response to the user.
        Safe to call even if no Speaker is attached (logs only).
        """
        if self._speaker:
            self._speaker.say(text)
        else:
            self.logger.info(f"[Response] {text}")

    def get_param(self, intent: Intent, key: str, default=None):
        """Convenience accessor for intent parameters."""
        return intent.params.get(key, default)
