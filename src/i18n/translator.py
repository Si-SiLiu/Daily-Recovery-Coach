"""UTF-8 JSON translation loading, fallback, and safe interpolation."""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from .locale import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, normalize_language
from .models import TranslationResource


LOGGER = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parents[2]
LOCALES_DIR = BASE_DIR / "locales"


def _lookup(messages: dict[str, Any], key: str) -> str | None:
    value: Any = messages
    for segment in key.split("."):
        if not isinstance(value, dict) or segment not in value:
            return None
        value = value[segment]
    return value if isinstance(value, str) else None


@lru_cache(maxsize=8)
def _load_messages(language: str, locales_dir_text: str) -> dict[str, Any]:
    path = Path(locales_dir_text) / f"{language}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("Unable to load locale %s: %s", language, exc)
        return {}
    if not isinstance(payload, dict):
        LOGGER.warning("Locale %s must contain a JSON object", language)
        return {}
    return payload


class Translator:
    """Translate one selected locale with deterministic default-language fallback."""

    def __init__(self, language: str = DEFAULT_LANGUAGE, locales_dir: Path | str = LOCALES_DIR):
        self.language = normalize_language(language)
        self.locales_dir = Path(locales_dir)

    @property
    def resource(self) -> TranslationResource:
        return TranslationResource(
            SUPPORTED_LANGUAGES[self.language],
            _load_messages(self.language, str(self.locales_dir.resolve())),
        )

    def translate(self, key: str, **values: object) -> str:
        messages = self.resource.messages
        text = _lookup(dict(messages), key)
        if text is None and self.language != DEFAULT_LANGUAGE:
            fallback = _load_messages(DEFAULT_LANGUAGE, str(self.locales_dir.resolve()))
            text = _lookup(fallback, key)
        if text is None:
            LOGGER.warning("Missing translation key %s for %s", key, self.language)
            return f"[missing: {key}]"
        if not values:
            return text
        try:
            return text.format(**values)
        except (KeyError, ValueError, IndexError) as exc:
            LOGGER.warning("Unable to format translation %s: %s", key, exc)
            return f"[format-error: {key}]"

    def __call__(self, key: str, **values: object) -> str:
        return self.translate(key, **values)


def get_translator(language: str = DEFAULT_LANGUAGE) -> Translator:
    return Translator(language)


def t(key: str, language: str = DEFAULT_LANGUAGE, **values: object) -> str:
    return get_translator(language)(key, **values)
