"""
utils/helpers.py — Shared utility functions
============================================
Small helpers used across multiple modules.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def slugify(text: str) -> str:
    """
    Convert a string to a URL-safe slug.

    Example:
        slugify("Hello, World!") → "hello-world"
    """
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")


def truncate(text: str, max_len: int = 60, ellipsis: str = "…") -> str:
    """Truncate a string for display/logging purposes."""
    if len(text) <= max_len:
        return text
    return text[:max_len - len(ellipsis)] + ellipsis


def sanitise_speech(text: str) -> str:
    """
    Remove characters that cause problems with TTS engines
    (URLs, excessive punctuation, markdown symbols).
    """
    # Strip URLs
    text = re.sub(r"https?://\S+", "a link", text)
    # Remove markdown bold/italic
    text = re.sub(r"[*_`#]", "", text)
    # Collapse multiple spaces
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def safe_import(module_name: str) -> Any:
    """
    Try to import a module and return it, or return None on ImportError.
    Useful for optional dependencies.

    Example:
        spacy = safe_import("spacy")
        if spacy is None:
            print("spaCy not installed")
    """
    import importlib

    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def format_duration(seconds: int) -> str:
    """
    Human-readable duration string.

    Examples:
        format_duration(90)   → "1 minute and 30 seconds"
        format_duration(3600) → "1 hour"
    """
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''}"

    minutes, secs = divmod(seconds, 60)
    hours, mins   = divmod(minutes, 60)

    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if mins:
        parts.append(f"{mins} minute{'s' if mins != 1 else ''}")
    if secs:
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")

    return " and ".join(parts[-2:]) if len(parts) > 1 else parts[0]
