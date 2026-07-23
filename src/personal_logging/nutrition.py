"""Nutrition aggregation that preserves unknown versus measured zero."""

from .config import NUTRITION_FIELDS


def summarize_nutrition_rows(rows):
    rows = [dict(row) for row in rows]
    summary = {"logged_meals": len({(row["meal_type"], row.get("meal_time")) for row in rows})}
    populated = 0
    possible = len(rows) * len(NUTRITION_FIELDS)
    for field in NUTRITION_FIELDS:
        values = [row[field] for row in rows if row.get(field) is not None]
        populated += len(values)
        summary[field] = round(sum(values), 2) if values else None
    summary["data_completeness"] = round(populated * 100 / possible) if possible else 0
    summary["is_complete"] = summary["data_completeness"] == 100
    return summary
