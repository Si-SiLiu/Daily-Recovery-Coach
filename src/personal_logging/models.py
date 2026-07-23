"""Typed records for local personal logging inputs."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BodyMeasurement:
    date: str
    weight_kg: float
    height_cm: float | None = None
    measurement_time: str | None = None
    waist_cm: float | None = None
    body_fat_percent: float | None = None
    is_primary: bool = False
    notes: str | None = None


@dataclass(frozen=True)
class NutritionLog:
    date: str
    meal_type: str
    food_name: str
    amount: float | None = None
    unit: str | None = None
    meal_time: str | None = None
    calories: float | None = None
    protein_g: float | None = None
    carbohydrate_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    water_ml: float | None = None
    sodium_mg: float | None = None
    notes: str | None = None
    data_source: str = "manual"


@dataclass(frozen=True)
class WorkoutSession:
    date: str
    session_type: str
    start_time: str | None = None
    end_time: str | None = None
    duration_minutes: float | None = None
    session_rpe: float | None = None
    energy_before: int | None = None
    energy_after: int | None = None
    soreness: int | None = None
    metadata: dict[str, Any] | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ExerciseSet:
    exercise_name: str
    set_number: int
    exercise_category: str | None = None
    reps: int | None = None
    weight_kg: float | None = None
    duration_seconds: float | None = None
    distance_m: float | None = None
    rpe: float | None = None
    rir: float | None = None
    tempo: str | None = None
    rest_seconds: float | None = None
    notes: str | None = None
