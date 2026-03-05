"""
core/dispatcher.py — Intent → Handler routing
==============================================
Discovers and loads all handler modules, then routes incoming Intents
to the handler that declares it can handle the given (action, target).

Adding a new handler:
    1. Create `handlers/my_handler.py` subclassing `BaseHandler`.
    2. Override `supported_intents()` to declare what it handles.
    3. That's it — the Dispatcher auto-discovers it on startup.
"""

import importlib
import pkgutil
from typing import Optional

from core.logger import get_logger
from core.parser import Intent
from handlers.base_handler import BaseHandler

logger = get_logger(__name__)


class Dispatcher:
    """
    Auto-discovers handler modules and routes Intents to the right one.

    Handler resolution order:
        1. Exact (action, target) match
        2. Action-only match (target == "")
        3. "unknown" fallback handler (if registered)
    """

    def __init__(self, speaker=None):
        """
        Args:
            speaker: Speaker instance passed to every handler so they
                     can generate voice feedback.
        """
        self.speaker = speaker
        self._handlers: dict[tuple[str, str], BaseHandler] = {}
        self._load_handlers()

    # ------------------------------------------------------------------ #
    #  Handler discovery                                                   #
    # ------------------------------------------------------------------ #

    def _load_handlers(self):
        """
        Iterate the `handlers` package and instantiate every concrete
        BaseHandler subclass found.  No explicit registration required.
        """
        import handlers  # the package

        for _finder, module_name, _ispkg in pkgutil.iter_modules(handlers.__path__):
            if module_name == "base_handler":
                continue  # skip abstract base

            try:
                module = importlib.import_module(f"handlers.{module_name}")
            except ImportError as exc:
                logger.warning(f"Could not import handlers.{module_name}: {exc}")
                continue

            # Find concrete BaseHandler subclasses in the module
            for attr_name in dir(module):
                cls = getattr(module, attr_name)
                if (
                    isinstance(cls, type)
                    and issubclass(cls, BaseHandler)
                    and cls is not BaseHandler
                    and not getattr(cls, "__abstractmethods__", None)
                ):
                    self._register(cls, module_name)

        logger.info(
            f"Loaded {len(set(self._handlers.values()))} handler(s) covering "
            f"{len(self._handlers)} intent key(s)."
        )

    def _register(self, handler_cls: type, module_name: str):
        """Instantiate a handler and register all its declared intents."""
        try:
            instance: BaseHandler = handler_cls(speaker=self.speaker)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Handler {handler_cls.__name__} failed to init: {exc}")
            return

        if not instance.is_available():
            logger.info(f"{handler_cls.__name__} is not available (missing deps/creds) — skipped.")
            return

        for action, target in instance.supported_intents():
            key = (action.lower(), target.lower())
            if key in self._handlers:
                logger.warning(
                    f"Intent key {key} already registered by "
                    f"{self._handlers[key].__class__.__name__}. "
                    f"{handler_cls.__name__} will not override it."
                )
            else:
                self._handlers[key] = instance
                logger.debug(f"  Registered: {key} → {handler_cls.__name__}")

    # ------------------------------------------------------------------ #
    #  Dispatch                                                            #
    # ------------------------------------------------------------------ #

    def dispatch(self, intent: Intent) -> bool:
        """
        Find and call the handler for this intent.

        Args:
            intent: Parsed Intent from the CommandParser.

        Returns:
            True if a handler was found and called, False otherwise.
        """
        handler = self._resolve(intent)

        if handler is None:
            logger.info(f"No handler found for: {intent}")
            if self.speaker:
                self.speaker.say(
                    f"Sorry, I don't know how to {intent.action.replace('_', ' ')} yet."
                )
            return False

        try:
            handler.handle(intent)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"Handler {handler.__class__.__name__} raised an error: {exc}",
                exc_info=True,
            )
            if self.speaker:
                self.speaker.say("I ran into a problem executing that command.")
            return False

    def _resolve(self, intent: Intent) -> Optional[BaseHandler]:
        """
        Try progressively looser key matches to find a handler.
        """
        action = intent.action.lower()
        target = intent.target.lower()

        # 1. Exact match
        handler = self._handlers.get((action, target))
        if handler:
            return handler

        # 2. Action-only match (handler declared target as "")
        handler = self._handlers.get((action, ""))
        if handler:
            return handler

        # 3. Target-only wildcard match ("*", target)
        handler = self._handlers.get(("*", target))
        if handler:
            return handler

        return None

    # ------------------------------------------------------------------ #
    #  Introspection                                                       #
    # ------------------------------------------------------------------ #

    def list_capabilities(self) -> list[tuple[str, str, str]]:
        """
        Return a sorted list of (action, target, handler_class) tuples.
        Useful for a "help" command.
        """
        return sorted(
            [
                (action, target, h.__class__.__name__)
                for (action, target), h in self._handlers.items()
            ],
            key=lambda x: x[0],
        )
