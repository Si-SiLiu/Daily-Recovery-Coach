"""Translation resource validation utilities."""

from collections.abc import Mapping
from typing import Any


class TranslationValidationError(ValueError):
    """Raised when locale resources do not share the same valid structure."""


def flatten_keys(messages: Mapping[str, Any], prefix: str = "") -> set[str]:
    """Return leaf translation keys from a nested resource."""
    keys: set[str] = set()
    for name, value in messages.items():
        key = f"{prefix}.{name}" if prefix else name
        if isinstance(value, Mapping):
            keys.update(flatten_keys(value, key))
        elif isinstance(value, str):
            keys.add(key)
        else:
            raise TranslationValidationError(f"Translation value must be text: {key}")
    return keys


def validate_matching_keys(resources: Mapping[str, Mapping[str, Any]]) -> set[str]:
    """Require every supplied locale resource to expose identical leaf keys."""
    key_sets = {language: flatten_keys(messages) for language, messages in resources.items()}
    if not key_sets:
        raise TranslationValidationError("At least one translation resource is required")
    reference_language, reference_keys = next(iter(key_sets.items()))
    for language, keys in key_sets.items():
        if keys != reference_keys:
            missing = sorted(reference_keys - keys)
            extra = sorted(keys - reference_keys)
            raise TranslationValidationError(
                f"{language} differs from {reference_language}; missing={missing}, extra={extra}"
            )
    return reference_keys
