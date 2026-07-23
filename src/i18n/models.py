"""Typed models used by the local translation engine."""

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Language:
    """A supported locale and its self-displayed name."""

    code: str
    native_name: str


@dataclass(frozen=True)
class TranslationResource:
    """A validated language resource loaded from disk."""

    language: Language
    messages: Mapping[str, Any]
