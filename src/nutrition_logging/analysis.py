"""Deterministic meal-energy estimate and category-balance assessment."""

from __future__ import annotations

from typing import Any


ANALYSIS_VERSION = "1.0.0"

# Category-level defaults are deliberately conservative. Entered food weights do
# not contain enough information for laboratory-grade calorie calculation.
KCAL_PER_UNIT = {
    "carbohydrate": 1.5,
    "protein": 2.0,
    "fat": 9.0,
    "vegetable": 0.3,
    "fruit": 0.6,
    "dairy": 0.65,
    "nuts": 6.0,
    "supplement": 0.0,
    "hydration": 0.0,
    "caffeine": 0.0,
    "alcohol": 0.7,
}

BALANCE_WEIGHTS = {
    "carbohydrate": 20,
    "protein": 25,
    "vegetable": 25,
    "fruit": 10,
    "fat": 5,
    "dairy": 10,
    "nuts": 5,
}


def analyze_meal_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    populated = {
        str(item.get("category"))
        for item in items
        if item.get("item_name") and float(item.get("quantity") or 0) > 0
    }
    calories = sum(
        max(float(item.get("quantity") or 0), 0.0)
        * KCAL_PER_UNIT.get(str(item.get("category")), 0.0)
        for item in items
        if item.get("item_name") and item.get("category") != "supplement"
    )
    score = sum(weight for category, weight in BALANCE_WEIGHTS.items() if category in populated)
    level = "balanced" if score >= 75 else "moderate" if score >= 45 else "needs_improvement"
    return {
        "estimated_calories_kcal": round(calories, 1),
        "balance_score": score,
        "balance_level": level,
        "analysis_version": ANALYSIS_VERSION,
    }
