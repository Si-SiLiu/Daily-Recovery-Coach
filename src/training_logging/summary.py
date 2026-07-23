"""Deterministic structured-training summaries; never used by Recovery Score."""

from __future__ import annotations

from collections import Counter


LB_TO_KG = 0.45359237
LOAD_CONVERSION_VERSION = "load-conversion-v1"
VOLUME_SET_TYPES = {"working", "backoff", "drop", "failure", "test"}


def summarize_training(exercises):
    active_exercises = [item for item in exercises if not item.get("deleted_at")]
    sets = [
        {**set_row, "exercise": exercise}
        for exercise in active_exercises
        for set_row in exercise.get("sets", [])
        if not set_row.get("deleted_at") and bool(set_row.get("completed"))
    ]
    volume_kg = 0.0
    volume_source_sets = 0
    for item in sets:
        if item.get("set_type") not in VOLUME_SET_TYPES:
            continue
        load, reps, unit = item.get("load_value"), item.get("reps"), item.get("load_unit")
        if load is None or reps is None or unit not in {"kg", "lb"}:
            continue
        converted = float(load) if unit == "kg" else float(load) * LB_TO_KG
        volume_kg += converted * int(reps)
        volume_source_sets += 1
    rpe_values = [float(item["rpe"]) for item in sets if item.get("rpe") is not None]
    muscle_counts = Counter()
    for item in sets:
        if item.get("set_type") == "warmup":
            continue
        muscle = item["exercise"].get("primary_muscle_group")
        if muscle:
            muscle_counts[muscle] += 1
    return {
        "exercise_count": len(active_exercises),
        "total_set_count": len(sets),
        "working_set_count": sum(item.get("set_type") == "working" for item in sets),
        "warmup_set_count": sum(item.get("set_type") == "warmup" for item in sets),
        "total_reps": sum(int(item["reps"]) for item in sets if item.get("reps") is not None),
        "strength_volume_load_kg": round(volume_kg, 2) if volume_source_sets else None,
        "load_conversion_version": LOAD_CONVERSION_VERSION,
        "average_rpe": round(sum(rpe_values) / len(rpe_values), 2) if rpe_values else None,
        "max_rpe": max(rpe_values) if rpe_values else None,
        "total_rest_seconds": round(sum(
            float(item["rest_seconds"]) for item in sets if item.get("rest_seconds") is not None
        ), 2),
        "muscle_group_set_counts": dict(sorted(muscle_counts.items())),
    }

