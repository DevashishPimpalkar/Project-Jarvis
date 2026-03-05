"""
handlers/system_handler.py — OS-level and utility commands
===========================================================
Handles time/date queries, countdown timers, and application launching.
No external APIs required — everything runs locally.

Supported intents:
    get_time   → Tell the current time
    get_date   → Tell today's date
    set_timer  → Start a countdown and announce when done
    open_app   → Launch an application by name
    shutdown   → (handled in main.py, but declared here for documentation)
"""

from __future__ import annotations

import subprocess
import threading
from datetime import datetime
from typing import Optional

from handlers.base_handler import BaseHandler
from core.parser import Intent


import platform as _platform

_OS = _platform.system()   # "Windows" | "Darwin" | "Linux"

# Map spoken app names → OS-specific launch commands.
# Add rows here freely — no other file needs changing.
APP_MAP: dict[str, dict[str, str]] = {
    # Browsers
    "chrome":        {"Windows": "start chrome",    "Darwin": "open -a 'Google Chrome'", "Linux": "google-chrome"},
    "google chrome": {"Windows": "start chrome",    "Darwin": "open -a 'Google Chrome'", "Linux": "google-chrome"},
    "firefox":       {"Windows": "start firefox",   "Darwin": "open -a Firefox",         "Linux": "firefox"},
    "edge":          {"Windows": "start msedge",    "Darwin": "open -a 'Microsoft Edge'","Linux": "microsoft-edge"},
    "safari":        {"Windows": "",                "Darwin": "open -a Safari",           "Linux": ""},
    "brave":         {"Windows": "start brave",     "Darwin": "open -a Brave",           "Linux": "brave-browser"},
    # Editors / IDEs
    "vs code":       {"Windows": "code",            "Darwin": "code",                    "Linux": "code"},
    "vscode":        {"Windows": "code",            "Darwin": "code",                    "Linux": "code"},
    "notepad":       {"Windows": "notepad",         "Darwin": "open -a TextEdit",        "Linux": "gedit"},
    "sublime":       {"Windows": "subl",            "Darwin": "subl",                    "Linux": "subl"},
    # Utilities
    "calculator":    {"Windows": "calc",            "Darwin": "open -a Calculator",      "Linux": "gnome-calculator"},
    "terminal":      {"Windows": "cmd",             "Darwin": "open -a Terminal",        "Linux": "gnome-terminal"},
    "file manager":  {"Windows": "explorer",        "Darwin": "open .",                  "Linux": "nautilus"},
    "files":         {"Windows": "explorer",        "Darwin": "open .",                  "Linux": "nautilus"},
    # Music / Comms
    "spotify":       {"Windows": "spotify",         "Darwin": "open -a Spotify",         "Linux": "spotify"},
    "discord":       {"Windows": "discord",         "Darwin": "open -a Discord",         "Linux": "discord"},
    "slack":         {"Windows": "slack",           "Darwin": "open -a Slack",           "Linux": "slack"},
    "zoom":          {"Windows": "zoom",            "Darwin": "open -a zoom.us",         "Linux": "zoom"},
    "teams":         {"Windows": "teams",           "Darwin": "open -a 'Microsoft Teams'","Linux": "teams"},
}


class SystemHandler(BaseHandler):
    """Handles OS-level commands: time, date, timers, and app launches."""

    def supported_intents(self) -> list[tuple[str, str]]:
        return [
            ("get_time",  "system"),
            ("get_date",  "system"),
            ("set_timer", "system"),
            ("open_app",  "system"),
        ]

    def is_available(self) -> bool:
        return True  # no external dependencies

    def handle(self, intent: Intent) -> None:
        action = intent.action

        if action == "get_time":
            self._get_time()
        elif action == "get_date":
            self._get_date()
        elif action == "set_timer":
            self._set_timer(intent)
        elif action == "open_app":
            self._open_app(intent)
        else:
            self.speak(f"Unknown system action: {action}")

    # ------------------------------------------------------------------ #
    #  Action implementations                                             #
    # ------------------------------------------------------------------ #

    def _get_time(self):
        """Announce the current local time."""
        now = datetime.now()
        # Cross-platform 12-hour format (%-I fails on Windows)
        hour = now.strftime("%I").lstrip("0") or "12"
        time_str = f"{hour}:{now.strftime('%M %p').lower()}"
        self.speak(f"The current time is {time_str}.")

    def _get_date(self):
        """Announce today's date."""
        today = datetime.now()
        # Ordinal suffix (1st, 2nd, 3rd …)
        day = today.day
        suffix = self._ordinal_suffix(day)
        date_str = today.strftime(f"%A, %B {day}{suffix} %Y")
        self.speak(f"Today is {date_str}.")

    def _set_timer(self, intent: Intent):
        """Start a non-blocking countdown timer."""
        amount = self.get_param(intent, "amount")
        unit   = self.get_param(intent, "unit", "second")

        if amount is None:
            self.speak("How long should the timer be?")
            return

        try:
            amount = int(amount)
        except (TypeError, ValueError):
            self.speak("I didn't understand the timer duration.")
            return

        # Convert to seconds
        unit = unit.lower().rstrip("s")  # normalise "minutes" → "minute"
        seconds = {
            "second": amount,
            "minute": amount * 60,
            "hour":   amount * 3600,
        }.get(unit, amount)

        # Pluralise for speech
        unit_display = f"{unit}{'s' if amount != 1 else ''}"
        self.speak(f"Setting a {amount} {unit_display} timer.")
        self.logger.info(f"Timer started: {seconds}s")

        def _countdown():
            threading.Event().wait(timeout=seconds)
            self.speak(f"Your {amount} {unit_display} timer is up!")

        t = threading.Thread(target=_countdown, daemon=True)
        t.start()

    def _open_app(self, intent: Intent):
        """Launch an application by spoken name."""
        app_name = (
            self.get_param(intent, "app")
            or self.get_param(intent, "query")
            or ""
        ).lower().strip()

        if not app_name:
            self.speak("Which application should I open?")
            return

        # Look up in the app map (partial match)
        cmd = self._resolve_app_command(app_name)

        if not cmd:
            self.speak(f"I don't know how to open {app_name}.")
            return

        try:
            # Use shell=True so commands like "open -a 'Google Chrome'" work correctly
            subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.speak(f"Opening {app_name}.")
            self.logger.info(f"Launched: {cmd}")
        except FileNotFoundError:
            self.speak(f"{app_name} doesn't appear to be installed.")
        except Exception as exc:  # noqa: BLE001
            self.logger.error(f"Failed to launch {cmd}: {exc}")
            self.speak(f"I couldn't open {app_name}.")

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _resolve_app_command(name: str) -> Optional[str]:
        """
        Return the OS-appropriate shell command for a spoken app name.
        Tries exact match, then partial/substring match.
        """
        name = name.lower().strip()

        def _cmd_for(entry: dict) -> Optional[str]:
            cmd = entry.get(_OS, "") or entry.get("Linux", "")
            return cmd if cmd else None

        # 1. Exact match
        if name in APP_MAP:
            return _cmd_for(APP_MAP[name])

        # 2. Partial match — spoken name contains or is contained by a key
        for key, cmds in APP_MAP.items():
            if key in name or name in key:
                return _cmd_for(cmds)

        return None

    @staticmethod
    def _ordinal_suffix(n: int) -> str:
        if 11 <= (n % 100) <= 13:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
