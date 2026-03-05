"""
core/logger.py — Centralised logging configuration
====================================================
Call `get_logger(__name__)` in every module to get a consistently
formatted logger that respects the LOG_LEVEL / LOG_FILE settings.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


_configured = False


def _configure_root_logger(level: str = "INFO", log_file: Optional[str] = None):
    global _configured
    if _configured:
        return
    _configured = True

    fmt = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # Optional file handler
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)


def get_logger(name: str) -> logging.Logger:
    """
    Return a module-level logger.  Call once at module import time:

        from core.logger import get_logger
        logger = get_logger(__name__)
    """
    # Lazy-init using settings (avoids circular import at module level)
    try:
        from config import settings
        _configure_root_logger(settings.LOG_LEVEL, settings.LOG_FILE)
    except ImportError:
        _configure_root_logger()

    return logging.getLogger(name)
