"""Central enums and fail-fast validation for structured training details."""

from __future__ import annotations

from datetime import date, time
import math


TRAINING_SOURCES = ("polar", "manual", "healthkit", "imported", "merged")
SPORT_TYPE_SOURCES = ("polar", "manual", "manual_override", "healthkit", "imported")
TRAINING_STATUSES = ("draft", "completed")
EXERCISE_CATEGORIES = (
    "strength", "bodyweight", "cardio", "mobility", "dance", "technique",
    "rehabilitation", "other",
)
MOVEMENT_PATTERNS = (
    "squat", "hinge", "push", "pull", "carry", "rotation", "locomotion",
    "isolation", "skill",
)
MEASUREMENT_MODES = (
    "weight_reps", "bodyweight_reps", "assisted_reps", "duration",
    "distance_duration", "dance_practice", "freeform",
)
SET_TYPES = (
    "warmup", "working", "backoff", "drop", "failure", "technique",
    "test", "other",
)
LOAD_UNITS = ("kg", "lb", "bodyweight", "assisted_kg", "none")
SIDES = ("bilateral", "left", "right", "alternating", "not_applicable")


def finite_number(name, value, minimum=None, maximum=None, integer=False):
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError(f"INVALID_{name.upper()}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_{name.upper()}") from exc
    if not math.isfinite(number):
        raise ValueError(f"INVALID_{name.upper()}")
    if integer and not number.is_integer():
        raise ValueError(f"INVALID_{name.upper()}")
    if minimum is not None and number < minimum:
        raise ValueError(f"INVALID_{name.upper()}")
    if maximum is not None and number > maximum:
        raise ValueError(f"INVALID_{name.upper()}")
    return int(number) if integer else number


def valid_date(value):
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError("INVALID_TRAINING_DATE") from exc


def valid_time(value):
    if value in (None, ""):
        return None
    try:
        return time.fromisoformat(str(value)).isoformat(timespec="seconds")
    except (TypeError, ValueError) as exc:
        raise ValueError("INVALID_TRAINING_TIME") from exc


def enum_value(name, value, allowed):
    if value not in allowed:
        raise ValueError(f"INVALID_{name.upper()}")
    return value


def text_value(value):
    return str(value or "").strip() or None

