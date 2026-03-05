"""
core/parser.py — Natural Language Understanding / Intent Extraction
====================================================================
Converts raw transcribed speech into structured `Intent` objects that
the Dispatcher can route to the correct handler.

Pipeline:
    raw text → normalise → rule-based fast path → AI fallback → Intent

Supported backends (config.PARSER_BACKEND):
    "spacy"  — Fully local. Uses spaCy + hand-crafted rule patterns.
               No internet required. ~10 ms per parse.
    "openai" — Uses OpenAI API for robust NLU. Requires API key.
    "grok"   — Uses xAI Grok API. Requires API key.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from core.logger import get_logger
from config import settings

logger = get_logger(__name__)


# ------------------------------------------------------------------ #
#  Intent data model                                                   #
# ------------------------------------------------------------------ #

@dataclass
class Intent:
    """
    Structured representation of a parsed voice command.

    Attributes:
        action:     Canonical action name e.g. "play_song", "search_web".
        target:     Target system e.g. "spotify", "browser".
        params:     Key-value parameters for the handler.
        raw_text:   Original transcribed speech for debugging.
        confidence: 0.0–1.0 confidence score (1.0 for rule-based matches).
    """
    action: str
    target: str                     = ""
    params: dict[str, Any]          = field(default_factory=dict)
    raw_text: str                   = ""
    confidence: float               = 1.0

    def __str__(self) -> str:
        return (
            f"Intent(action={self.action!r}, target={self.target!r}, "
            f"params={self.params}, confidence={self.confidence:.2f})"
        )


# ------------------------------------------------------------------ #
#  Intent catalogue                                                    #
# ------------------------------------------------------------------ #

INTENT_CATALOGUE: dict[str, dict] = {
    "play_song":      {"target": "spotify", "description": "Play a specific song"},
    "play_playlist":  {"target": "spotify", "description": "Play a playlist"},
    "pause_music":    {"target": "spotify", "description": "Pause playback"},
    "resume_music":   {"target": "spotify", "description": "Resume playback"},
    "skip_track":     {"target": "spotify", "description": "Skip to next track"},
    "volume_up":      {"target": "spotify", "description": "Increase volume"},
    "volume_down":    {"target": "spotify", "description": "Decrease volume"},
    "now_playing":    {"target": "spotify", "description": "What is playing"},
    "open_url":       {"target": "browser", "description": "Open a specific URL"},
    "search_web":     {"target": "browser", "description": "Search the web"},
    "open_youtube":   {"target": "browser", "description": "Open YouTube or search it"},
    "play_youtube":   {"target": "browser", "description": "Play a YouTube video"},
    "shutdown":       {"target": "system",  "description": "Shut down JARVIS"},
    "open_app":       {"target": "system",  "description": "Open an application"},
    "set_timer":      {"target": "system",  "description": "Set a countdown timer"},
    "get_time":       {"target": "system",  "description": "Tell the current time"},
    "get_date":       {"target": "system",  "description": "Tell today's date"},
    "get_weather":    {"target": "weather", "description": "Get weather for a city"},

    # Small talk / conversational
    "small_talk":     {"target": "chat",    "description": "Casual conversation and greetings"},
}


# ------------------------------------------------------------------ #
#  Command parser                                                      #
# ------------------------------------------------------------------ #

class CommandParser:
    """
    Main NLU pipeline. Tries rule-based matching first (fast, offline),
    then falls back to the configured AI backend for anything unclear.
    """

    def __init__(self):
        self._nlp = None
        self._load_spacy()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def parse(self, text: str) -> Optional[Intent]:
        """
        Parse a raw transcription into a structured Intent.

        Args:
            text: Raw speech transcription.

        Returns:
            An Intent, or None if the input cannot be understood.
        """
        if not text or not text.strip():
            return None

        normalised = self._normalise(text)
        logger.debug(f"Parsing: '{normalised}'")

        # 1. Fast rule-based path
        intent = self._rule_based_parse(normalised)
        if intent:
            logger.debug(f"Rule match: {intent}")
            return intent

        # 2. AI backend fallback
        if settings.PARSER_BACKEND in ("openai", "grok"):
            intent = self._ai_parse(normalised)
            if intent:
                logger.debug(f"AI match: {intent}")
                return intent

        # 3. spaCy semantic fallback
        intent = self._spacy_fallback(normalised)
        if intent:
            return intent

        logger.info(f"Could not parse: '{normalised}'")
        return None

    # ------------------------------------------------------------------ #
    #  Normalisation                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalise(text: str) -> str:
        """Lower-case and strip wake-word prefix artefacts from STT."""
        text = text.lower().strip()
        for wake in ("hey jarvis", "ok jarvis", "jarvis"):
            if text.startswith(wake):
                text = text[len(wake):].strip(" ,")
        return text

    # ------------------------------------------------------------------ #
    #  Rule-based parser  (all regex groups verified against real inputs)  #
    # ------------------------------------------------------------------ #

    def _rule_based_parse(self, text: str) -> Optional[Intent]:
        """
        Fast offline pattern matching.  Every regex here is tested.
        Add new patterns freely — no other file needs changing.
        """

        # ── Shutdown ────────────────────────────────────────────────── #
        if re.search(r"\b(shutdown|shut down|goodbye|bye|exit|quit)\b", text):
            return Intent("shutdown", "system", raw_text=text)

        # ── Time & date ──────────────────────────────────────────────── #
        # Handles: "what time is it", "what is the time", "what's the time"
        if re.search(r"what(?:'s| is)(?: the)? time\b|time is it\b", text):
            return Intent("get_time", "system", raw_text=text)

        # Handles: "what's today's date", "what is the date", "what day is it"
        if re.search(r"what(?:'s| is)(?: today'?s?)?(?: the)? date\b|what day is it", text):
            return Intent("get_date", "system", raw_text=text)

        # ── YouTube (must precede generic Spotify play) ───────────────── #
        # "play [query] on youtube"
        m = re.search(r"play\s+(.+?)\s+on\s+youtube", text)
        if m:
            return Intent(
                "play_youtube", "browser",
                params={"query": m.group(1).strip()},
                raw_text=text,
            )

        # "open/launch youtube"
        if re.search(r"\b(open|go to|launch|show)\s+youtube\b", text):
            return Intent("open_youtube", "browser", raw_text=text)

        # ── Spotify ──────────────────────────────────────────────────── #
        # "play [song]", "play [song] by [artist]", "play [song] on spotify"
        # FIX: removed the erroneous \s+ before optional suffix groups
        m = re.search(
            r"^play\s+(.+?)(?:\s+by\s+(.+?))?(?:\s+on\s+(?:spotify|music))?$",
            text,
        )
        if m:
            song   = m.group(1).strip()
            artist = (m.group(2) or "").strip()
            return Intent(
                "play_song", "spotify",
                params={"song": song, "artist": artist},
                raw_text=text,
            )

        if re.search(r"\b(pause|stop)\b.{0,20}(music|song|track|spotify|playing)?", text):
            return Intent("pause_music", "spotify", raw_text=text)

        if re.search(r"\b(resume|continue|unpause)\b.{0,20}(music|song|spotify)?", text):
            return Intent("resume_music", "spotify", raw_text=text)

        if re.search(r"\b(skip|next)\b.{0,15}(track|song)?", text):
            return Intent("skip_track", "spotify", raw_text=text)

        if re.search(r"\bvolume up\b|\bincrease volume\b|\blouder\b|turn it up", text):
            return Intent("volume_up", "spotify", raw_text=text)

        if re.search(r"\bvolume down\b|\bdecrease volume\b|\bquieter\b|turn it down", text):
            return Intent("volume_down", "spotify", raw_text=text)

        if re.search(r"\bwhat(?:'s| is)(?: this| the| currently)? playing\b", text):
            return Intent("now_playing", "spotify", raw_text=text)

        # ── Web search ───────────────────────────────────────────────── #
        # FIX: was incorrectly using m.group(2); only one capture group exists
        m = re.search(r"(?:search(?: for| the web for)?|google|look up)\s+(.+)", text)
        if m:
            return Intent(
                "search_web", "browser",
                params={"query": m.group(1).strip()},
                raw_text=text,
            )

        # ── Open URL ─────────────────────────────────────────────────── #
        m = re.search(
            r"\b(?:open|go to|navigate to|visit)\s+(https?://\S+|\w[\w.-]+\.\w{2,})",
            text,
        )
        if m:
            url = m.group(1)
            if not url.startswith("http"):
                url = "https://" + url
            return Intent(
                "open_url", "browser",
                params={"url": url},
                raw_text=text,
            )

        # ── Open app (must come AFTER open_url and open_youtube) ─────── #
        # Catches: "open chrome", "launch spotify", "start notepad"
        m = re.search(
            r"\b(?:open|launch|start|run)\s+([a-zA-Z][a-zA-Z0-9 ]{1,30})\b",
            text,
        )
        if m:
            return Intent(
                "open_app", "system",
                params={"app": m.group(1).strip()},
                raw_text=text,
            )

        # ── Weather ──────────────────────────────────────────────────── #
        m = re.search(r"\bweather\b(?:.*?\bin\s+([a-zA-Z ]+))?", text)
        if m:
            city = (m.group(1) or settings.DEFAULT_CITY).strip()
            return Intent(
                "get_weather", "weather",
                params={"city": city},
                raw_text=text,
            )

        # ── Set timer ────────────────────────────────────────────────── #
        m = re.search(
            r"set(?: a)? timer\s+(?:for\s+)?(\d+)\s+(second|minute|hour)s?",
            text,
        )
        if m:
            return Intent(
                "set_timer", "system",
                params={"amount": int(m.group(1)), "unit": m.group(2)},
                raw_text=text,
            )

        # ── Small talk (always last — never swallows a real command) ──── #
        if re.search(
            r"\b(hello|hi|hey|howdy|greetings|good morning|good evening|good afternoon"
            r"|how are you|how'?s it going|what'?s up|sup|yo"
            r"|who are you|what are you|what can you do|help me"
            r"|thank(?:s| you)|cheers|nice one|great job)\b",
            text,
        ):
            return Intent("small_talk", "chat", params={"text": text}, raw_text=text)

        return None

    # ------------------------------------------------------------------ #
    #  AI parser                                                           #
    # ------------------------------------------------------------------ #

    def _ai_parse(self, text: str) -> Optional[Intent]:
        """Call the configured AI API to classify an ambiguous command."""
        prompt = self._build_ai_prompt(text)
        try:
            raw = self._call_openai(prompt) if settings.PARSER_BACKEND == "openai" \
                  else self._call_grok(prompt)
            return self._parse_ai_response(raw, text)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"AI parser error: {exc}")
            return None

    def _build_ai_prompt(self, text: str) -> str:
        catalogue_summary = "\n".join(
            f"  - {action}: {meta['description']} (target: {meta['target']})"
            for action, meta in INTENT_CATALOGUE.items()
        )
        return f"""You are an intent classifier for a voice assistant called JARVIS.

Available intents:
{catalogue_summary}

Classify this command: "{text}"

Respond ONLY with valid JSON (no markdown fences):
{{"action": "<action or null>", "target": "<target>", "params": {{}}, "confidence": 0.9}}"""

    def _call_openai(self, prompt: str) -> str:
        import openai  # type: ignore
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=0,
        )
        return resp.choices[0].message.content or ""

    def _call_grok(self, prompt: str) -> str:
        import openai  # Grok uses OpenAI-compatible SDK
        client = openai.OpenAI(
            api_key=settings.GROK_API_KEY,
            base_url=settings.GROK_BASE_URL,
        )
        resp = client.chat.completions.create(
            model=settings.GROK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=0,
        )
        return resp.choices[0].message.content or ""

    @staticmethod
    def _parse_ai_response(raw: str, original_text: str) -> Optional[Intent]:
        try:
            cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
            data = json.loads(cleaned)
            action = data.get("action")
            if not action or action == "null":
                return None
            return Intent(
                action=action,
                target=data.get("target", ""),
                params=data.get("params", {}),
                raw_text=original_text,
                confidence=float(data.get("confidence", 0.8)),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning(f"Could not parse AI response: {exc}\nRaw: {raw!r}")
            return None

    # ------------------------------------------------------------------ #
    #  spaCy fallback                                                      #
    # ------------------------------------------------------------------ #

    def _load_spacy(self):
        try:
            import spacy  # type: ignore
            self._nlp = spacy.load(settings.SPACY_MODEL)
            logger.info(f"spaCy model '{settings.SPACY_MODEL}' loaded.")
        except ImportError:
            logger.warning("spaCy not installed. Run: pip install spacy")
        except OSError:
            logger.warning(
                f"spaCy model '{settings.SPACY_MODEL}' not found. "
                f"Run: python -m spacy download {settings.SPACY_MODEL}"
            )

    def _spacy_fallback(self, text: str) -> Optional[Intent]:
        if self._nlp is None:
            return None
        doc = self._nlp(text)
        verbs = [t.lemma_ for t in doc if t.pos_ == "VERB"]
        nouns = [t.lemma_ for t in doc if t.pos_ in ("NOUN", "PROPN")]

        if any(v in verbs for v in ("play", "listen", "start")):
            return Intent("play_song", "spotify",
                          params={"song": " ".join(nouns) or text},
                          raw_text=text, confidence=0.5)
        if any(v in verbs for v in ("search", "find", "look", "google")):
            return Intent("search_web", "browser",
                          params={"query": text},
                          raw_text=text, confidence=0.5)
        if any(v in verbs for v in ("open", "launch", "show")):
            return Intent("open_url", "browser",
                          params={"query": text},
                          raw_text=text, confidence=0.4)
        return None
