"""Pure presentation rules for the structured-training entry UI.

These helpers deliberately do not write to SQLite and do not calculate training
summaries.  They decide what the editor displays while preserving the complete
exercise/set dictionaries owned by the existing training service.
"""

from __future__ import annotations

from uuid import uuid4


TRAINING_ENTRY_UI_VERSION = "1.0.0"
ENTRY_MODES = ("simple", "advanced")
EXERTION_PREFERENCES = ("rpe", "rir", "none")

_CORE_FIELDS = {
    "weight_reps": ("load_value", "load_unit", "reps"),
    "bodyweight_reps": ("load_value", "load_unit", "reps"),
    "assisted_reps": ("load_value", "load_unit", "reps"),
    "duration": ("duration_seconds",),
    "distance_duration": ("distance_meters", "duration_seconds"),
    "dance_practice": ("duration_seconds",),
    "freeform": ("duration_seconds",),
}


def default_load_unit(measurement_mode: str) -> str:
    return {
        "weight_reps": "kg",
        "bodyweight_reps": "bodyweight",
        "assisted_reps": "assisted_kg",
    }.get(measurement_mode, "none")


def visible_set_fields(
    measurement_mode: str,
    entry_mode: str = "simple",
    exertion_preference: str = "rpe",
) -> tuple[str, ...]:
    """Return ordered fields that are relevant to the current editor state."""
    if entry_mode not in ENTRY_MODES:
        raise ValueError("INVALID_TRAINING_ENTRY_MODE")
    if exertion_preference not in EXERTION_PREFERENCES:
        raise ValueError("INVALID_EXERTION_PREFERENCE")
    if measurement_mode not in _CORE_FIELDS:
        raise ValueError("INVALID_MEASUREMENT_MODE")

    fields = list(_CORE_FIELDS[measurement_mode])
    if entry_mode == "simple":
        if exertion_preference != "none":
            fields.append(exertion_preference)
        if measurement_mode in {"dance_practice", "freeform"}:
            fields.append("notes")
        return tuple(fields)

    if measurement_mode not in {"dance_practice", "freeform"}:
        fields.insert(0, "set_type")
    if measurement_mode == "distance_duration":
        fields.extend(("resistance_level", "incline_percent"))
    fields.append("rpe")
    if measurement_mode not in {"dance_practice", "freeform"}:
        fields.append("rir")
    fields.extend(("rest_seconds", "side", "completed", "notes"))
    return tuple(dict.fromkeys(fields))


def apply_catalog_defaults(exercise: dict, catalog_item: dict) -> dict:
    """Apply authoritative catalog metadata without fabricating set values."""
    result = dict(exercise)
    result.update({
        "exercise_catalog_id": catalog_item["id"],
        "custom_exercise_name": None,
        "exercise_category": catalog_item["exercise_category"],
        "measurement_mode": catalog_item["measurement_mode"],
        "primary_muscle_group": catalog_item.get("primary_muscle_group") or "",
        "equipment": catalog_item.get("equipment") or "",
        "is_unilateral": bool(catalog_item.get("is_unilateral")),
        "_catalog_applied_id": catalog_item["id"],
    })
    unit = default_load_unit(catalog_item["measurement_mode"])
    result["sets"] = []
    for set_row in exercise.get("sets") or []:
        copied = dict(set_row)
        if copied.get("load_unit") in (None, "none", "bodyweight"):
            copied["load_unit"] = unit
        if unit in {"bodyweight", "none"}:
            copied["load_value"] = None
        result["sets"].append(copied)
    return result


def copied_set_for_entry(
    source: dict,
    measurement_mode: str,
    entry_mode: str,
    exertion_preference: str,
    *,
    completed: bool = True,
) -> dict:
    """Copy only applicable values and always create a new unsaved identity."""
    allowed = set(visible_set_fields(measurement_mode, entry_mode, exertion_preference))
    allowed.update({"set_type", "load_unit", "side"})
    result = {key: value for key, value in source.items() if key in allowed}
    result["uuid"] = str(uuid4())
    result["completed"] = bool(completed)
    result.setdefault("set_type", "working")
    result.setdefault("load_unit", default_load_unit(measurement_mode))
    result.setdefault("side", "not_applicable")
    return result
