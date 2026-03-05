"""
JARVIS - Voice-Activated AI Assistant
======================================
Main event loop. Continuously listens for the wake word or push-to-talk,
pipes speech through the command parser, and dispatches to handlers.

Usage:
    python main.py                  # Wake-word mode (say "Hey Jarvis")
    python main.py --push-to-talk   # Hold Enter to speak
    python main.py --once           # Process one command and exit
"""

import sys
import time
import signal
import argparse
import threading
from pathlib import Path

# Ensure project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).parent))

from core.logger import get_logger
from core.listener import Listener
from core.speaker import Speaker
from core.parser import CommandParser
from core.dispatcher import Dispatcher
from config import settings

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JARVIS Voice Assistant")
    parser.add_argument("--push-to-talk", action="store_true",
                        help="Press Enter to start/stop recording instead of wake word")
    parser.add_argument("--once", action="store_true",
                        help="Listen for a single command then exit")
    parser.add_argument("--no-voice", action="store_true",
                        help="Suppress spoken responses (text only)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable verbose debug logging")
    return parser.parse_args()


class JARVIS:
    """
    Top-level orchestrator. Wires together all subsystems and runs
    the main listen → parse → dispatch → respond loop.
    """

    def __init__(self, push_to_talk: bool = False, silent: bool = False):
        self.push_to_talk = push_to_talk
        self._running = False

        logger.info("Initialising JARVIS subsystems…")

        self.listener   = Listener()
        self.speaker    = Speaker(silent=silent)
        self.parser     = CommandParser()
        self.dispatcher = Dispatcher(speaker=self.speaker)

        # Register a clean shutdown on Ctrl-C
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    def start(self):
        """Enter the main listen-parse-dispatch loop."""
        self._running = True
        self.speaker.say(settings.STARTUP_MESSAGE)
        logger.info("JARVIS is online. Listening for commands.")

        if self.push_to_talk:
            self._push_to_talk_loop()
        else:
            self._wake_word_loop()

    def stop(self):
        """Gracefully shut down all subsystems."""
        self._running = False
        self.speaker.say("Shutting down. Goodbye.")
        logger.info("JARVIS shutting down.")

    # ------------------------------------------------------------------ #
    #  Listening loops                                                     #
    # ------------------------------------------------------------------ #

    def _wake_word_loop(self):
        """
        Passive background loop: always-on microphone that waits for the
        configured wake word before capturing the full command.
        """
        logger.info(f"Wake-word mode active. Say '{settings.WAKE_WORD}' to activate.")

        while self._running:
            try:
                # Short ambient capture to check for wake word
                snippet = self.listener.listen_for_wake_word(
                    wake_word=settings.WAKE_WORD,
                    timeout=settings.WAKE_WORD_TIMEOUT,
                )

                if snippet:
                    logger.debug(f"Wake word detected in: '{snippet}'")
                    self.speaker.play_activation_chime()

                    # Capture the actual command after activation
                    command_text = self.listener.listen_for_command(
                        timeout=settings.COMMAND_TIMEOUT,
                        phrase_limit=settings.PHRASE_LIMIT,
                    )

                    if command_text:
                        self._handle_command(command_text)
                    else:
                        self.speaker.say("I didn't catch that. Please try again.")

            except Exception as exc:  # noqa: BLE001
                logger.error(f"Error in wake-word loop: {exc}", exc_info=True)
                time.sleep(0.5)  # brief back-off before retrying

    def _push_to_talk_loop(self):
        """
        Interactive mode: press Enter to start recording, press Enter again
        (or wait for silence) to finish.
        """
        print("\n[Push-to-Talk] Press ENTER to speak, Ctrl-C to quit.\n")

        while self._running:
            try:
                input("  🎙  Press ENTER to speak… ")
                self.speaker.play_activation_chime()
                print("  🔴  Recording… (speak now)")

                command_text = self.listener.listen_for_command(
                    timeout=settings.COMMAND_TIMEOUT,
                    phrase_limit=settings.PHRASE_LIMIT,
                )

                if command_text:
                    print(f"  📝  Heard: \"{command_text}\"")
                    self._handle_command(command_text)
                else:
                    print("  ⚠   Nothing detected.")
                    self.speaker.say("I didn't catch that.")

            except KeyboardInterrupt:
                break
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Error in push-to-talk loop: {exc}", exc_info=True)

    # ------------------------------------------------------------------ #
    #  Command pipeline                                                    #
    # ------------------------------------------------------------------ #

    def _handle_command(self, text: str):
        """
        Full pipeline for a single recognised utterance:
          1. Parse → extract intent + parameters
          2. Dispatch → find and call the right handler
          3. Any handler errors are caught here so the loop continues
        """
        logger.info(f"Processing command: '{text}'")

        try:
            intent = self.parser.parse(text)
            logger.debug(f"Parsed intent: {intent}")

            if not intent:
                self.speaker.say("Sorry, I didn't understand that command.")
                return

            # Shutdown is a special meta-command handled here
            if intent.action == "shutdown":
                self.stop()
                return

            self.dispatcher.dispatch(intent)

        except Exception as exc:  # noqa: BLE001
            logger.error(f"Unhandled error during command processing: {exc}", exc_info=True)
            self.speaker.say("I ran into an error processing that command.")

    # ------------------------------------------------------------------ #
    #  Signal handling                                                     #
    # ------------------------------------------------------------------ #

    def _handle_shutdown(self, signum, frame):  # noqa: ANN001
        logger.info(f"Received signal {signum}. Initiating shutdown.")
        self.stop()
        sys.exit(0)


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

def main():
    args = parse_args()

    if args.debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    jarvis = JARVIS(
        push_to_talk=args.push_to_talk,
        silent=args.no_voice,
    )

    if args.once:
        # Single-shot mode for testing
        text = jarvis.listener.listen_for_command(
            timeout=settings.COMMAND_TIMEOUT,
            phrase_limit=settings.PHRASE_LIMIT,
        )
        if text:
            print(f"Heard: '{text}'")
            jarvis._handle_command(text)
        else:
            print("Nothing detected.")
    else:
        jarvis.start()


if __name__ == "__main__":
    main()
