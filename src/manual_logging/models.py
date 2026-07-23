"""Typed inputs for the manual health logging engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ManualActivitySession:
    date: str
    start_time: str | None = None
    end_time: str | None = None
    duration_minutes: float | None = None
    activity_type: str | None = None
    activity_name: str | None = None
    average_hr_bpm: float | None = None
    max_hr_bpm: float | None = None
    calories_kcal: float | None = None
    fat_burn_percentage: float | None = None
    distance_m: float | None = None
    session_rpe: float | None = None
    notes: str | None = None
    linked_polar_session_id: str | None = None
    confirmed_by_user: bool = False


@dataclass(frozen=True)
class ManualSleepLog:
    sleep_date: str
    bed_time: str | None = None
    sleep_start_time: str | None = None
    wake_time: str | None = None
    get_up_time: str | None = None
    sleep_duration_minutes: float | None = None
    nap_duration_minutes: float | None = None
    subjective_sleep_quality: int | None = None
    awakenings: int | None = None
    notes: str | None = None
    total_sleep_duration_minutes: float | None = None
    actual_sleep_duration_minutes: float | None = None
    deep_sleep_duration_minutes: float | None = None
    rem_sleep_duration_minutes: float | None = None
    average_sleep_hr_bpm: float | None = None
    minimum_sleep_hr_bpm: float | None = None
    nightly_hrv_rmssd: float | None = None
    respiration_rate: float | None = None


@dataclass(frozen=True)
class ManualRecoveryLog:
    date: str
    measurement_time: str | None = None
    subjective_recovery: int | None = None
    fatigue: int | None = None
    muscle_soreness: int | None = None
    mental_energy: int | None = None
    training_motivation: int | None = None
    stress_level: int | None = None
    pain_present: bool = False
    pain_location: str | None = None
    notes: str | None = None
    morning_rmssd_ms: float | None = None
    morning_resting_hr_bpm: float | None = None
