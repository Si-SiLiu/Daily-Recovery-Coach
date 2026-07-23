"""JSON Schema loader and local validator."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator


BASE_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = BASE_DIR / "config" / "ai_context_export.schema.json"


def validate_export(payload):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda item: list(item.path))
    if errors:
        path = ".".join(str(part) for part in errors[0].path) or "$"
        raise ValueError(f"AI_CONTEXT_SCHEMA_INVALID:{path}")
    return payload
