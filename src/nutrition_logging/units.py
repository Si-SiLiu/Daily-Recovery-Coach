"""Authoritative supplement-unit enum and presentation helpers."""

from __future__ import annotations

from enum import StrEnum
import math


class SupplementUnit(StrEnum):
    G = "g"
    MG = "mg"
    MCG = "mcg"
    ML = "ml"
    CAPSULE = "capsule"
    TABLET = "tablet"
    SACHET = "sachet"
    SCOOP = "scoop"
    DROP = "drop"
    IU = "iu"


SUPPLEMENT_UNITS = tuple(unit.value for unit in SupplementUnit)
COUNT_UNITS = {"capsule", "tablet", "sachet", "scoop", "drop"}


def normalize_unit(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in SUPPLEMENT_UNITS:
        raise ValueError("INVALID_SUPPLEMENT_UNIT")
    return normalized


def positive_finite(value: object, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_{field.upper()}") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"INVALID_{field.upper()}")
    return number


def unit_label_key(unit: str) -> str:
    return f"nutrition_entry.units.{normalize_unit(unit)}"
