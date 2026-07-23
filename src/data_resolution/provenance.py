"""Helpers that preserve source identity while adapting database records."""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from .models import SourceCandidate


ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+(?:\.\d+)?)D)?"
    r"(?:T(?:(?P<hours>\d+(?:\.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)


def row_to_dict(cursor: sqlite3.Cursor, row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return dict(row)
    return dict(zip((column[0] for column in cursor.description), row))


def query_one(
    connection: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()
) -> dict[str, Any] | None:
    cursor = connection.execute(query, params)
    return row_to_dict(cursor, cursor.fetchone())


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    cursor = connection.execute(f"PRAGMA table_info({table})")
    rows = cursor.fetchall()
    if rows and isinstance(rows[0], sqlite3.Row):
        return {str(row["name"]) for row in rows}
    return {str(row[1]) for row in rows}


def parse_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        payload = json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "":
            return value
    return None


def nested(mapping: dict[str, Any], *path: str) -> Any:
    value: Any = mapping
    for key in path:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def number(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def duration_minutes(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value) / 60.0
    text = str(value).strip()
    if text.lower().endswith("s") and not text.startswith("P"):
        seconds = number(text[:-1])
        return seconds / 60.0 if seconds is not None else None
    match = ISO_DURATION_RE.fullmatch(text)
    if not match:
        return None
    days = float(match.group("days") or 0)
    hours = float(match.group("hours") or 0)
    minutes = float(match.group("minutes") or 0)
    seconds = float(match.group("seconds") or 0)
    return days * 1440 + hours * 60 + minutes + seconds / 60


def candidate(value: Any, record: dict[str, Any] | None, *, confirmed: bool = False) -> SourceCandidate:
    return SourceCandidate(value, record.get("id") if record else None, confirmed)
