"""Fail-fast validation for local user-entered records."""

from datetime import date
from typing import Any

from .config import DATA_SOURCES, MEAL_TYPES, SESSION_TYPES


class PersonalLoggingValidationError(ValueError):
    """Raised when a personal logging field violates its local contract."""


def validate_date(value: str) -> str:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise PersonalLoggingValidationError("INVALID_DATE") from exc
    return value


def optional_range(name: str, value: float | None, low: float, high: float | None = None) -> None:
    if value is None:
        return
    if value < low or (high is not None and value > high):
        raise PersonalLoggingValidationError(f"INVALID_{name.upper()}")


def validate_body(data: dict[str, Any]) -> dict[str, Any]:
    validate_date(data["date"])
    optional_range("weight_kg", data.get("weight_kg"), 0.01)
    optional_range("height_cm", data.get("height_cm"), 0.01)
    optional_range("waist_cm", data.get("waist_cm"), 0.01)
    optional_range("body_fat_percent", data.get("body_fat_percent"), 0, 100)
    if data.get("weight_kg") is None:
        raise PersonalLoggingValidationError("WEIGHT_REQUIRED")
    return data


def validate_nutrition(data: dict[str, Any]) -> dict[str, Any]:
    validate_date(data["date"])
    if data.get("meal_type") not in MEAL_TYPES:
        raise PersonalLoggingValidationError("INVALID_MEAL_TYPE")
    if not str(data.get("food_name") or "").strip():
        raise PersonalLoggingValidationError("FOOD_NAME_REQUIRED")
    if data.get("data_source", "manual") not in DATA_SOURCES:
        raise PersonalLoggingValidationError("INVALID_DATA_SOURCE")
    for name in ("amount", "calories", "protein_g", "carbohydrate_g", "fat_g",
                 "fiber_g", "water_ml", "sodium_mg"):
        optional_range(name, data.get(name), 0)
    return data


def validate_session(data: dict[str, Any]) -> dict[str, Any]:
    validate_date(data["date"])
    if data.get("session_type") not in SESSION_TYPES:
        raise PersonalLoggingValidationError("INVALID_SESSION_TYPE")
    optional_range("duration_minutes", data.get("duration_minutes"), 0)
    optional_range("session_rpe", data.get("session_rpe"), 0, 10)
    for name in ("energy_before", "energy_after", "soreness"):
        optional_range(name, data.get(name), 0, 10)
    return data


def validate_set(data: dict[str, Any]) -> dict[str, Any]:
    if not str(data.get("exercise_name") or "").strip():
        raise PersonalLoggingValidationError("EXERCISE_NAME_REQUIRED")
    optional_range("set_number", data.get("set_number"), 1)
    for name in ("reps", "weight_kg", "duration_seconds", "distance_m", "rpe",
                 "rir", "rest_seconds"):
        optional_range(name, data.get(name), 0, 10 if name == "rpe" else None)
    return data
