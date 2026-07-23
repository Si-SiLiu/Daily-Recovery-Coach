"""Validation contract for manually entered meal events and category items."""

from __future__ import annotations

from datetime import date, time
from typing import Any
import math

from .supplements import validate_supplement


class NutritionEventValidationError(ValueError):
    """Raised when a meal event violates the normalized local contract."""


MEAL_TYPES = (
    "breakfast", "morning_snack", "lunch", "afternoon_snack", "dinner",
    "training_fuel", "bedtime_fuel", "free_snack",
)
CORE_CATEGORIES = (
    "carbohydrate", "protein", "fat", "vegetable", "fruit", "dairy", "nuts",
)
EXTENDED_CATEGORIES = ("supplement", "hydration", "caffeine", "alcohol")
CATEGORIES = CORE_CATEGORIES + EXTENDED_CATEGORIES
EXTENDED_MEALS = {
    "breakfast", "morning_snack", "lunch", "afternoon_snack", "dinner",
}
FIXED_UNITS = {
    **{category: "g" for category in CORE_CATEGORIES + ("caffeine",)},
    "hydration": "ml", "alcohol": "ml",
}
NAME_OPTIONAL = {"hydration", "caffeine", "alcohol"}


def categories_for_meal(meal_type: str) -> tuple[str, ...]:
    return CATEGORIES if meal_type in EXTENDED_MEALS else CORE_CATEGORIES


def validate_meal_event(event: dict[str, Any], items: list[dict[str, Any]]) -> None:
    try:
        date.fromisoformat(str(event.get("date")))
    except (TypeError, ValueError) as exc:
        raise NutritionEventValidationError("INVALID_MEAL_DATE") from exc
    meal_type = event.get("meal_type")
    if meal_type not in MEAL_TYPES:
        raise NutritionEventValidationError("INVALID_MEAL_TYPE")
    try:
        time.fromisoformat(str(event.get("actual_meal_time")))
    except (TypeError, ValueError) as exc:
        raise NutritionEventValidationError("INVALID_ACTUAL_MEAL_TIME") from exc

    allowed = set(categories_for_meal(meal_type))
    seen: set[tuple[str, int]] = set()
    counts: dict[str, int] = {}
    for item in items:
        category = item.get("category")
        if category not in allowed:
            raise NutritionEventValidationError("CATEGORY_NOT_ALLOWED_FOR_MEAL")
        try:
            position = int(item.get("position"))
        except (TypeError, ValueError) as exc:
            raise NutritionEventValidationError("INVALID_ITEM_POSITION") from exc
        if not 1 <= position <= 5 or (category, position) in seen:
            raise NutritionEventValidationError("INVALID_ITEM_POSITION")
        seen.add((category, position)); counts[category] = counts.get(category, 0) + 1
        if counts[category] > 5:
            raise NutritionEventValidationError("TOO_MANY_ITEMS_IN_CATEGORY")
        if category not in NAME_OPTIONAL and not str(item.get("item_name") or "").strip():
            raise NutritionEventValidationError("ITEM_NAME_REQUIRED")
        try:
            quantity = float(item.get("quantity"))
        except (TypeError, ValueError) as exc:
            raise NutritionEventValidationError("INVALID_ITEM_QUANTITY") from exc
        if not math.isfinite(quantity) or quantity <= 0:
            raise NutritionEventValidationError("INVALID_ITEM_QUANTITY")
        if category == "supplement":
            try:
                validate_supplement(item)
            except ValueError as exc:
                raise NutritionEventValidationError(str(exc)) from exc
            continue
        unit = item.get("unit")
        fixed = FIXED_UNITS.get(category)
        if fixed and unit != fixed:
            raise NutritionEventValidationError("INVALID_ITEM_UNIT_FOR_CATEGORY")
