"""Structured input model for the local deterministic coach."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CoachInput:
    date: str
    recovery_score: int | None = None
    score_version: str | None = None
    recovery_capacity_score: float | None = None
    stress_load_score: float | None = None
    overall_confidence_score: int | None = None
    confidence_level: str | None = None
    data_completeness: int | None = None
    fallback_used: bool = False
    sleep_duration_hours: float | None = None
    sleep_score: float | None = None
    nightly_hrv_rmssd: float | None = None
    nightly_resting_hr: float | None = None
    respiration_rate: float | None = None
    morning_rmssd: float | None = None
    morning_mean_hr: float | None = None
    kubios_readiness: Any = None
    previous_training_duration_minutes: float | None = None
    previous_training_calories: float | None = None
    active_calories: float | None = None
    training_count: int | None = None
    baseline_status: dict[str, str] = field(default_factory=dict)
    explanation_json: dict[str, Any] = field(default_factory=dict)
    freshness_days: int = 0
    is_historical: bool = False
