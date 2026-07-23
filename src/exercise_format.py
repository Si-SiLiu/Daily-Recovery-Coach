"""Formatting and validation helpers for exercise table values."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


_HMS_PATTERN = re.compile(r"^(\d{2,}):([0-5]\d):([0-5]\d)$")


def minutes_to_hms(value: Any) -> str | None:
    """Render duration minutes as an editable HH:MM:SS value."""
    if value in (None, ""):
        return None
    total_seconds = round(float(value) * 60)
    if total_seconds < 0:
        raise ValueError("duration cannot be negative")
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def hms_to_minutes(value: Any) -> float | None:
    """Parse HH:MM:SS into the minutes stored by the canonical data model."""
    if value in (None, ""):
        return None
    matched = _HMS_PATTERN.fullmatch(str(value).strip())
    if not matched:
        raise ValueError("运动时长必须使用 HH:MM:SS 格式，例如 01:25:23")
    hours, minutes, seconds = (int(part) for part in matched.groups())
    return (hours * 3600 + minutes * 60 + seconds) / 60


def hours_to_hms(value: Any) -> str | None:
    """Render a numeric hour value as HH:MM:SS."""
    if value in (None, ""):
        return None
    return minutes_to_hms(float(value) * 60)


def time_to_hms(value: Any) -> str | None:
    """Render an ISO datetime or clock time as HH:MM:SS."""
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text).strftime("%H:%M:%S")
    except ValueError:
        matched = re.fullmatch(r"(\d{1,2}):([0-5]\d)(?::([0-5]\d))?", text)
        if not matched:
            return text
        hour, minute, second = matched.groups()
        return f"{int(hour):02d}:{minute}:{second or '00'}"
