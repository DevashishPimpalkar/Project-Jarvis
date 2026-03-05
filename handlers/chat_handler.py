"""
handlers/chat_handler.py — Small talk and conversational responses
==================================================================
Handles casual speech that isn't a command: greetings, "how are you",
"what can you do", thank-yous, etc.

If an OpenAI/Grok key is configured it generates a dynamic reply.
Otherwise it uses a built-in response bank (fully offline, instant).

Supported intents:
    small_talk → chat
"""

from __future__ import annotations

import random
import re
from handlers.base_handler import BaseHandler
from core.parser import Intent
from config import settings


# ------------------------------------------------------------------ #
#  Offline response bank                                              #
# ------------------------------------------------------------------ #

# Keys are regex patterns; values are lists of possible responses
# (one is chosen at random so JARVIS doesn't sound robotic).
_RESPONSES: list[tuple[str, list[str]]] = [
    # Greetings
    (r"\b(hello|hi|hey|howdy|greetings)\b", [
        "Hey! What can I do for you?",
        "Hello! Ready to help.",
        "Hi there! What do you need?",
    ]),
    # Good morning / evening
    (r"\bgood (morning|afternoon|evening)\b", [
        "Good {0}! How can I help you today?",
        "Good {0}! What would you like me to do?",
    ]),
    # How are you
    (r"\bhow are you\b|\bhow'?s it going\b|\bhow'?s everything\b", [
        "I'm doing great, thanks for asking! What can I help you with?",
        "All systems running smoothly! What do you need?",
        "Ready and operational. What's on your mind?",
    ]),
    # What's up
    (r"\bwhat'?s up\b|\bsup\b|\byo\b", [
        "Not much — waiting for your command!",
        "Ready to help. What do you need?",
    ]),
    # Who are you / what are you
    (r"\bwho are you\b|\bwhat are you\b", [
        "I'm JARVIS, your voice-activated AI assistant. I can control Spotify, "
        "search the web, check the weather, set timers, and a lot more.",
        "I'm JARVIS — your personal AI assistant. Try saying things like "
        "'play some music', 'search for Python tutorials', or 'what's the weather'.",
    ]),
    # What can you do / help
    (r"\bwhat can you do\b|\bhelp( me)?\b|\bcommands\b|\bwhat do you know\b", [
        "Here's what I can do: play music on Spotify, search the web, "
        "open YouTube, check the weather, set timers, tell you the time or date, "
        "and open apps. Just ask!",
        "I can control Spotify, search Google, open YouTube videos, "
        "check weather, launch apps, and set timers. What would you like?",
    ]),
    # Thank you
    (r"\bthank(s| you)\b|\bcheers\b|\bnice one\b|\bgreat job\b", [
        "Happy to help!",
        "Anytime!",
        "You're welcome!",
        "Of course — let me know if you need anything else.",
    ]),
    # Compliments
    (r"\byou'?re (awesome|amazing|great|the best|cool|smart)\b", [
        "Thanks! You're not so bad yourself.",
        "I appreciate that! Is there anything else I can do for you?",
    ]),
]

_FALLBACK_RESPONSES = [
    "I'm not sure how to respond to that, but I'm great at playing music, "
    "searching the web, and checking the weather. Try one of those!",
    "Hmm, that's not something I can answer, but I can control Spotify, "
    "open YouTube, set timers, and more. What would you like?",
    "I didn't quite catch the meaning of that. Want me to search the web for it?",
]


class ChatHandler(BaseHandler):
    """Responds to casual conversation and greetings."""

    def supported_intents(self) -> list[tuple[str, str]]:
        return [("small_talk", "chat")]

    def is_available(self) -> bool:
        return True  # always available — no dependencies

    def handle(self, intent: Intent) -> None:
        text = intent.params.get("text", "").lower()

        # Try AI reply if a key is configured
        if settings.PARSER_BACKEND in ("openai", "grok") and (
            settings.OPENAI_API_KEY or settings.GROK_API_KEY
        ):
            reply = self._ai_reply(intent.raw_text)
            if reply:
                self.speak(reply)
                return

        # Offline pattern matching
        reply = self._offline_reply(text)
        self.speak(reply)

    # ------------------------------------------------------------------ #
    #  Response selection                                                  #
    # ------------------------------------------------------------------ #

    def _offline_reply(self, text: str) -> str:
        """Match text against response bank; fall back to generic reply."""
        for pattern, responses in _RESPONSES:
            m = re.search(pattern, text)
            if m:
                reply = random.choice(responses)
                # Allow {0} substitution for patterns that capture a group
                try:
                    if m.lastindex:
                        reply = reply.format(*m.groups())
                except (IndexError, KeyError):
                    pass
                return reply
        return random.choice(_FALLBACK_RESPONSES)

    def _ai_reply(self, text: str) -> str | None:
        """Generate a short conversational reply via the AI API."""
        try:
            import openai  # type: ignore

            if settings.PARSER_BACKEND == "grok":
                client = openai.OpenAI(
                    api_key=settings.GROK_API_KEY,
                    base_url=settings.GROK_BASE_URL,
                )
                model = settings.GROK_MODEL
            else:
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                model = settings.OPENAI_MODEL

            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are JARVIS, a concise voice assistant. "
                            "Reply in 1-2 short sentences, no markdown. "
                            "Stay friendly and helpful."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                max_tokens=80,
                temperature=0.7,
            )
            return (resp.choices[0].message.content or "").strip()

        except Exception as exc:  # noqa: BLE001
            self.logger.debug(f"AI chat reply failed, using offline: {exc}")
            return None
