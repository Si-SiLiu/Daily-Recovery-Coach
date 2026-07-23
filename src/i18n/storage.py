"""Local, non-health preference persistence for interface language."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .locale import DEFAULT_LANGUAGE, normalize_language


BASE_DIR = Path(__file__).resolve().parents[2]
PREFERENCES_PATH = BASE_DIR / "config" / "user_preferences.json"


def load_preferences(path: Path | str = PREFERENCES_PATH) -> dict[str, str]:
    """Load safe preferences, falling back when the file is absent or damaged."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"language": DEFAULT_LANGUAGE}
    if not isinstance(payload, dict):
        return {"language": DEFAULT_LANGUAGE}
    return {"language": normalize_language(payload.get("language"))}


def load_language_preference(path: Path | str = PREFERENCES_PATH) -> str:
    """Return the saved interface language or Simplified Chinese."""
    return load_preferences(path)["language"]


def save_language_preference(
    language: str,
    path: Path | str = PREFERENCES_PATH,
) -> str:
    """Atomically and idempotently persist only the normalized language code."""
    target = Path(path)
    normalized = normalize_language(language)
    content = json.dumps({"language": normalized}, ensure_ascii=False, indent=2) + "\n"
    try:
        if target.read_text(encoding="utf-8") == content:
            return normalized
    except OSError:
        pass
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=target.parent, delete=False
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, target)
    return normalized
