"""
demo.py — Keyboard-driven JARVIS demo (no microphone required)
==============================================================
Type commands at the prompt instead of speaking them.
All other logic (parser, dispatcher, handlers) runs exactly as in
production — only the voice I/O layer is bypassed.

Usage:
    python demo.py              # Interactive typed-command loop
    python demo.py --check      # Just verify imports & print status
    python demo.py --test       # Run built-in command test suite

This is the best starting point when you've just set up the project
and want to verify everything works before plugging in a mic.
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ------------------------------------------------------------------ #
#  Minimal mock speaker (prints instead of speaking)                  #
# ------------------------------------------------------------------ #

class _PrintSpeaker:
    """Drop-in Speaker replacement that prints responses instead of playing audio."""

    def say(self, text: str):
        print(f"\n  🤖  JARVIS: {text}\n")

    def say_async(self, text: str):
        self.say(text)

    def play_activation_chime(self):
        print("  🔔  [chime]")


# ------------------------------------------------------------------ #
#  Status check                                                        #
# ------------------------------------------------------------------ #

def run_check():
    """Print a colour-coded status for every dependency and credential."""
    print("\n" + "=" * 60)
    print("  JARVIS — System Status Check")
    print("=" * 60)

    checks = []

    # Python version
    v = sys.version_info
    ok = v >= (3, 10)
    checks.append((ok, f"Python {v.major}.{v.minor}.{v.micro}", "Requires 3.10+"))

    # Core packages
    optional_pkgs = {
        "speech_recognition": ("SpeechRecognition", "pip install SpeechRecognition pyaudio"),
        "pyttsx3":            ("pyttsx3",            "pip install pyttsx3"),
        "spacy":              ("spaCy",              "pip install spacy && python -m spacy download en_core_web_sm"),
        "spotipy":            ("Spotipy",            "pip install spotipy"),
        "openai":             ("OpenAI SDK",         "pip install openai"),
        "requests":           ("requests",           "pip install requests"),
    }
    for mod, (label, install_cmd) in optional_pkgs.items():
        try:
            __import__(mod)
            checks.append((True, label, ""))
        except ImportError:
            checks.append((None, label, f"Optional — install with: {install_cmd}"))

    # Config values
    try:
        from config import settings
        cfg_items = [
            (bool(settings.SPOTIFY_CLIENT_ID),  "Spotify Client ID",     "Set SPOTIFY_CLIENT_ID in .env"),
            (bool(settings.SPOTIFY_CLIENT_SECRET), "Spotify Secret",     "Set SPOTIFY_CLIENT_SECRET in .env"),
            (bool(settings.WEATHER_API_KEY),    "Weather API Key",        "Set WEATHER_API_KEY in .env"),
            (bool(settings.OPENAI_API_KEY),     "OpenAI API Key",         "Set OPENAI_API_KEY in .env (optional)"),
        ]
        checks.extend([(ok, label, hint) for ok, label, hint in cfg_items])
    except Exception as exc:
        checks.append((False, "config.py", str(exc)))

    for status, label, hint in checks:
        if status is True:
            icon = "✅"
        elif status is False:
            icon = "❌"
        else:
            icon = "⚠️ "
        suffix = f"  ← {hint}" if hint else ""
        print(f"  {icon}  {label}{suffix}")

    print()


# ------------------------------------------------------------------ #
#  Built-in test suite                                                 #
# ------------------------------------------------------------------ #

def run_tests():
    """Parse a batch of commands and print results without executing them."""
    from core.parser import CommandParser

    print("\n" + "=" * 60)
    print("  Parser Test Suite")
    print("=" * 60)

    parser = CommandParser()
    commands = [
        "play Bohemian Rhapsody by Queen",
        "play Blinding Lights on spotify",
        "play never gonna give you up on youtube",
        "what time is it",
        "what's the time",
        "what is the date",
        "search for machine learning tutorials",
        "google the weather in Paris",
        "open github.com",
        "open youtube",
        "pause the music",
        "skip this track",
        "volume up",
        "volume down",
        "what is currently playing",
        "weather in London",
        "set a timer for 10 minutes",
        "goodbye",
        "some completely unrecognised gibberish command xyz",
    ]

    passed = failed = 0
    for cmd in commands:
        intent = parser.parse(cmd)
        if intent:
            passed += 1
            print(f"  ✅  \"{cmd}\"")
            print(f"       → {intent.action} | target={intent.target} | params={intent.params}")
        else:
            failed += 1
            print(f"  ❌  \"{cmd}\"  (no match)")

    total = passed + failed
    print(f"\n  Result: {passed}/{total} commands parsed successfully\n")


# ------------------------------------------------------------------ #
#  Interactive loop                                                    #
# ------------------------------------------------------------------ #

def run_interactive():
    """Type commands and watch JARVIS respond — exactly like voice mode."""
    from core.parser import CommandParser
    from core.dispatcher import Dispatcher

    speaker    = _PrintSpeaker()
    parser     = CommandParser()
    dispatcher = Dispatcher(speaker=speaker)

    print("\n" + "=" * 60)
    print("  JARVIS — Interactive Demo (keyboard mode)")
    print("  Type a command, or 'quit' to exit.")
    print("  Type 'help' to see all registered handlers.")
    print("=" * 60 + "\n")

    speaker.say("All systems online. Type a command to get started.")

    while True:
        try:
            text = input("  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue

        if text.lower() in ("quit", "exit", "q"):
            speaker.say("Goodbye!")
            break

        if text.lower() == "help":
            caps = dispatcher.list_capabilities()
            print("\n  Registered capabilities:")
            for action, target, handler in caps:
                print(f"    {action:25s} → {handler}  (target: {target or 'any'})")
            print()
            continue

        intent = parser.parse(text)
        if not intent:
            print(f"  ⚠️   Could not parse: \"{text}\"")
            speaker.say("Sorry, I didn't understand that.")
            continue

        print(f"  🔍  Intent: {intent.action} → {intent.target} | {intent.params}")
        dispatcher.dispatch(intent)


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

def main():
    ap = argparse.ArgumentParser(description="JARVIS keyboard demo")
    ap.add_argument("--check", action="store_true", help="Run status check only")
    ap.add_argument("--test",  action="store_true", help="Run built-in parser tests")
    args = ap.parse_args()

    if args.check:
        run_check()
    elif args.test:
        run_tests()
    else:
        run_check()       # always show status first
        run_interactive()


if __name__ == "__main__":
    main()
