"""
handlers/example_custom_handler.py — TEMPLATE for new handlers
===============================================================
Copy this file, rename it, and fill in the three sections marked
with TODO.  The Dispatcher will auto-discover it on the next run.

Steps to add a new voice command:
    1. cp handlers/example_custom_handler.py handlers/my_handler.py
    2. Rename the class
    3. Fill in supported_intents(), is_available(), handle()
    4. Add any new action names to core/parser.py → INTENT_CATALOGUE
    5. Add rule patterns in CommandParser._rule_based_parse() (optional)
    6. Done — no other files need editing

Example: a "joke" handler
    supported_intents → [("tell_joke", "")]
    handle            → fetches a random joke from an API and speaks it
    is_available      → checks the `requests` package is installed
"""

from handlers.base_handler import BaseHandler
from core.parser import Intent


class ExampleCustomHandler(BaseHandler):
    """
    TODO: Rename this class to something descriptive, e.g. JokeHandler.
    """

    # ------------------------------------------------------------------ #
    #  TODO 1 — Declare which intents this handler processes              #
    # ------------------------------------------------------------------ #

    def supported_intents(self) -> list[tuple[str, str]]:
        """
        Return (action, target) pairs.
        Use "" as target to match any target for that action.

        Example:
            return [
                ("tell_joke", ""),
                ("fetch_quote", ""),
            ]
        """
        return [
            # ("my_action", "my_target"),
        ]

    # ------------------------------------------------------------------ #
    #  TODO 2 — Check prerequisites                                       #
    # ------------------------------------------------------------------ #

    def is_available(self) -> bool:
        """
        Return True if all required packages and credentials are present.

        Example:
            try:
                import requests
                return True
            except ImportError:
                self.logger.warning("requests not installed.")
                return False
        """
        return True  # replace with real check

    # ------------------------------------------------------------------ #
    #  TODO 3 — Implement the command logic                               #
    # ------------------------------------------------------------------ #

    def handle(self, intent: Intent) -> None:
        """
        Execute the command.  Read params from intent.params.
        Call self.speak(text) to give voice feedback.

        Example:
            if intent.action == "tell_joke":
                joke = fetch_random_joke()
                self.speak(joke)
        """
        # Read a parameter
        # value = self.get_param(intent, "my_param", default="fallback")

        # Respond verbally
        self.speak("This is a placeholder response from the example handler.")
