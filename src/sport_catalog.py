"""Resolve Polar Dynamic API sport identifiers using a locally cached catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SPORT_CATALOG_PATH = BASE_DIR / "data" / "raw" / "polar_sports.json"

# User-confirmed Polar identifiers. These deliberately take precedence over the
# cached Dynamic API catalog because older catalog snapshots can contain an
# incorrect localized label for these IDs.
SPORT_ID_OVERRIDES = {
    "15": "力量训练",
    "36": "田径运动",
    "83": "室内活动",
    "121": "表演舞",
}


def _items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("sports", "sportProfiles", "items"):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
    return []


def _identifier(item: dict) -> str | None:
    value = item.get("id") or item.get("sportId") or item.get("sport_id")
    if isinstance(value, dict):
        value = value.get("id") or value.get("value")
    return str(value) if value not in (None, "") else None


def _localized_name(item: dict, language: str) -> str | None:
    names = item.get("localizedNames") or item.get("localized_names")
    if not isinstance(names, dict):
        return None
    normalized = {str(key).lower(): value for key, value in names.items()}
    candidates = (language.lower(), language.split("-")[0].lower(), "en")
    for key in candidates:
        value = normalized.get(key)
        if isinstance(value, dict):
            value = value.get("name") or value.get("longName") or value.get("shortName")
        if value:
            return str(value)
    return None


def load_sport_catalog(path: Path | str = SPORT_CATALOG_PATH, language: str = "zh-CN") -> dict[str, str]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        return {}
    result = {}
    for item in _items(payload):
        identifier = _identifier(item)
        name = _localized_name(item, language) or item.get("name") or item.get("displayName")
        if identifier and name:
            result[identifier] = str(name)
    return result


def resolve_sport_name(value: Any, *, language: str = "zh-CN", path: Path | str = SPORT_CATALOG_PATH) -> str | None:
    if isinstance(value, dict):
        explicit = _localized_name(value, language) or value.get("name") or value.get("displayName")
        if explicit:
            return str(explicit)
        value = value.get("id") or value.get("code")
        if isinstance(value, dict):
            value = value.get("id") or value.get("value")
    if value in (None, ""):
        return None
    text = str(value)
    if not text.isdigit():
        return text
    return (
        SPORT_ID_OVERRIDES.get(text)
        or load_sport_catalog(path, language).get(text)
        or f"未知运动（ID {text}）"
    )
