"""Fail-fast validation for manually entered health records."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any


class ManualLoggingValidationError(ValueError):
    """Raised when a manual health field violates its local contract."""


def _required_date(data: dict[str, Any], field: str) -> None:
    try:
        date.fromisoformat(str(data[field]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ManualLoggingValidationError(f"INVALID_{field.upper()}") from exc


def _optional_time(data: dict[str, Any], field: str) -> None:
    value = data.get(field)
    if value in (None, ""):
        return
    text = str(value).strip()
    try:
        if "T" in text or " " in text:
            datetime.fromisoformat(text)
        else:
            time.fromisoformat(text)
    except ValueError as exc:
        raise ManualLoggingValidationError(f"INVALID_{field.upper()}") from exc


def _optional_number(
    data: dict[str, Any], field: str, minimum: float, maximum: float | None = None
) -> None:
    value = data.get(field)
    if value is None:
        return
    if isinstance(value, bool):
        raise ManualLoggingValidationError(f"INVALID_{field.upper()}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ManualLoggingValidationError(f"INVALID_{field.upper()}") from exc
    if number < minimum or (maximum is not None and number > maximum):
        raise ManualLoggingValidationError(f"INVALID_{field.upper()}")


def _optional_integer(
    data: dict[str, Any], field: str, minimum: int, maximum: int | None = None
) -> None:
    value = data.get(field)
    if value is None:
        return
    if isinstance(value, bool):
        raise ManualLoggingValidationError(f"INVALID_{field.upper()}")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ManualLoggingValidationError(f"INVALID_{field.upper()}") from exc
    if number != value or number < minimum or (maximum is not None and number > maximum):
        raise ManualLoggingValidationError(f"INVALID_{field.upper()}")


def validate_activity(data: dict[str, Any]) -> dict[str, Any]:
    _required_date(data, "date")
    for field in ("start_time", "end_time"):
        _optional_time(data, field)
    for field in ("duration_minutes", "calories_kcal", "distance_m"):
        _optional_number(data, field, 0)
    for field in ("average_hr_bpm", "max_hr_bpm"):
        _optional_number(data, field, 20, 300)
    _optional_number(data, "fat_burn_percentage", 0, 100)
    _optional_number(data, "session_rpe", 1, 10)
    if (
        data.get("average_hr_bpm") is not None
        and data.get("max_hr_bpm") is not None
        and float(data["average_hr_bpm"]) > float(data["max_hr_bpm"])
    ):
        raise ManualLoggingValidationError("AVERAGE_HR_EXCEEDS_MAX_HR")
    return data


def validate_sleep(data: dict[str, Any]) -> dict[str, Any]:
    _required_date(data, "sleep_date")
    for field in ("bed_time", "sleep_start_time", "wake_time", "get_up_time"):
        _optional_time(data, field)
    for field in (
        "sleep_duration_minutes", "nap_duration_minutes",
        "total_sleep_duration_minutes", "actual_sleep_duration_minutes",
        "deep_sleep_duration_minutes", "rem_sleep_duration_minutes",
    ):
        _optional_number(data, field, 0, 1440)
    for field in ("average_sleep_hr_bpm", "minimum_sleep_hr_bpm"):
        _optional_number(data, field, 20, 300)
    _optional_number(data, "nightly_hrv_rmssd", 0.01)
    _optional_number(data, "respiration_rate", 1, 80)
    if (
        data.get("average_sleep_hr_bpm") is not None
        and data.get("minimum_sleep_hr_bpm") is not None
        and float(data["minimum_sleep_hr_bpm"]) > float(data["average_sleep_hr_bpm"])
    ):
        raise ManualLoggingValidationError("MINIMUM_SLEEP_HR_EXCEEDS_AVERAGE")
    _optional_integer(data, "subjective_sleep_quality", 1, 10)
    _optional_integer(data, "awakenings", 0)
    return data


def validate_recovery(data: dict[str, Any]) -> dict[str, Any]:
    _required_date(data, "date")
    _optional_time(data, "measurement_time")
    for field in (
        "subjective_recovery",
        "fatigue",
        "muscle_soreness",
        "mental_energy",
        "training_motivation",
        "stress_level",
    ):
        _optional_integer(data, field, 1, 10)
    pain_present = data.get("pain_present")
    if pain_present not in (None, False, True, 0, 1):
        raise ManualLoggingValidationError("INVALID_PAIN_PRESENT")
    _optional_number(data, "morning_rmssd_ms", 0.01)
    _optional_number(data, "morning_resting_hr_bpm", 20, 300)
    return data
