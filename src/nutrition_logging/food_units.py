"""Stable units for ordinary food and beverage intake."""

from __future__ import annotations

from enum import StrEnum
import math


class FoodUnit(StrEnum):
    G = "g"
    KG = "kg"
    ML = "ml"
    L = "l"
    PIECE = "piece"
    SLICE = "slice"
    SERVING = "serving"
    BOWL = "bowl"
    CUP = "cup"
    SPOON = "spoon"
    BOTTLE = "bottle"
    PACK = "pack"


FOOD_UNITS = tuple(unit.value for unit in FoodUnit)
FOOD_COUNT_UNITS = {
    "piece", "slice", "serving", "bowl", "cup", "spoon", "bottle", "pack",
}


def normalize_food_unit(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in FOOD_UNITS:
        raise ValueError("INVALID_FOOD_UNIT")
    return normalized


def positive_food_quantity(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("INVALID_FOOD_QUANTITY") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError("INVALID_FOOD_QUANTITY")
    return number


def food_unit_label_key(unit: str) -> str:
    return f"simple_nutrition.units.{normalize_food_unit(unit)}"
