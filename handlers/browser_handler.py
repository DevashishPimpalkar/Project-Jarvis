"""
handlers/browser_handler.py — Browser navigation and web search
================================================================
Opens URLs, performs web searches, and navigates to YouTube — all
via Python's built-in `webbrowser` module (zero extra dependencies).

Supported intents:
    open_url      → Open an explicit URL
    search_web    → Google/DuckDuckGo search
    open_youtube  → Open YouTube homepage or search results
    play_youtube  → Search for and open a YouTube video
"""

from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus

from handlers.base_handler import BaseHandler
from core.parser import Intent
from config import settings


# ------------------------------------------------------------------ #
#  URL templates                                                       #
# ------------------------------------------------------------------ #

YOUTUBE_BASE    = "https://www.youtube.com"
YOUTUBE_SEARCH  = "https://www.youtube.com/results?search_query="
GOOGLE_SEARCH   = "https://www.google.com/search?q="
DDGO_SEARCH     = "https://duckduckgo.com/?q="


class BrowserHandler(BaseHandler):
    """Opens browser windows and performs web searches."""

    # ------------------------------------------------------------------ #
    #  BaseHandler interface                                               #
    # ------------------------------------------------------------------ #

    def supported_intents(self) -> list[tuple[str, str]]:
        return [
            ("open_url",     "browser"),
            ("search_web",   "browser"),
            ("open_youtube", "browser"),
            ("play_youtube", "browser"),
        ]

    def is_available(self) -> bool:
        # webbrowser is a stdlib module — always available
        return True

    def handle(self, intent: Intent) -> None:
        action = intent.action

        if action == "open_url":
            self._open_url(intent)
        elif action == "search_web":
            self._search_web(intent)
        elif action == "open_youtube":
            self._open_youtube(intent)
        elif action == "play_youtube":
            self._play_youtube(intent)
        else:
            self.speak(f"Unknown browser action: {action}")

    # ------------------------------------------------------------------ #
    #  Action implementations                                             #
    # ------------------------------------------------------------------ #

    def _open_url(self, intent: Intent):
        """Navigate directly to a URL."""
        url = self.get_param(intent, "url", "")

        # Allow a bare query string to fall back to a search
        if not url and (query := self.get_param(intent, "query")):
            self._do_search(query)
            return

        if not url:
            self.speak("I need a URL to open.")
            return

        # Prepend scheme if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        self.logger.info(f"Opening URL: {url}")
        self._open(url)
        self.speak(f"Opening {self._friendly_domain(url)}.")

    def _search_web(self, intent: Intent):
        """Perform a web search using the configured search engine."""
        query = self.get_param(intent, "query", "")
        if not query:
            self.speak("What would you like me to search for?")
            return

        self._do_search(query)

    def _open_youtube(self, intent: Intent):
        """Open the YouTube homepage, or search YouTube if a query is given."""
        query = self.get_param(intent, "query", "")

        if query:
            url = YOUTUBE_SEARCH + quote_plus(query)
            self.speak(f"Searching YouTube for {query}.")
        else:
            url = YOUTUBE_BASE
            self.speak("Opening YouTube.")

        self.logger.info(f"YouTube: {url}")
        self._open(url)

    def _play_youtube(self, intent: Intent):
        """Search YouTube for a video (same as open_youtube with a query)."""
        query = self.get_param(intent, "query", "")
        if not query:
            # Fall back to homepage
            self._open(YOUTUBE_BASE)
            self.speak("Opening YouTube.")
            return

        url = YOUTUBE_SEARCH + quote_plus(query)
        self.logger.info(f"YouTube search: {url}")
        self._open(url)
        self.speak(f"Searching YouTube for {query}.")

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _do_search(self, query: str):
        """Build a search URL using the configured engine and open it."""
        engine_url = settings.DEFAULT_SEARCH_ENGINE or GOOGLE_SEARCH
        url = engine_url + quote_plus(query)
        self.logger.info(f"Web search: {url}")
        self._open(url)
        self.speak(f"Searching for {query}.")

    def _open(self, url: str):
        """
        Open `url` in the configured browser (or system default).
        Runs in the foreground — webbrowser.open is non-blocking.
        """
        if settings.DEFAULT_BROWSER:
            try:
                browser = webbrowser.get(settings.DEFAULT_BROWSER)
                browser.open(url)
                return
            except webbrowser.Error:
                self.logger.warning(
                    f"Browser '{settings.DEFAULT_BROWSER}' not found; "
                    "using system default."
                )
        webbrowser.open(url)

    @staticmethod
    def _friendly_domain(url: str) -> str:
        """Extract a clean domain name for speech (e.g., 'github.com')."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.lstrip("www.")
        except Exception:
            return url
