"""Public internationalization interface for display-layer consumers."""

from .formatters import (
    format_date,
    format_datetime,
    format_duration,
    format_number,
    format_percent,
)
from .locale import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, normalize_language
from .storage import load_language_preference, save_language_preference
from .translator import Translator, get_translator, t

__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "Translator",
    "format_date",
    "format_datetime",
    "format_duration",
    "format_number",
    "format_percent",
    "get_translator",
    "load_language_preference",
    "normalize_language",
    "save_language_preference",
    "t",
]
