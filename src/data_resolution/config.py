"""Versioned configuration loader for canonical source policies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "data_source_priority.json"
DATA_RESOLUTION_VERSION = "1.1.0"


def load_policy_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if payload.get("version") != DATA_RESOLUTION_VERSION:
        raise ValueError("UNSUPPORTED_DATA_RESOLUTION_POLICY_VERSION")
    if not isinstance(payload.get("domains"), dict):
        raise ValueError("INVALID_DATA_RESOLUTION_POLICY")
    return payload
