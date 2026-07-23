"""Personal nutrition baseline derived from completed meal records."""

from __future__ import annotations

from datetime import date, timedelta
from statistics import median


BASELINE_METRICS = (
    "calories_kcal", "protein_g", "carbohydrate_g", "fat_g", "fiber_g", "water_ml",
)


def calculate_personal_nutrition_baseline(
    records: list[dict], end_date: str, window_days: int = 28, min_days: int = 3,
) -> dict:
    """Calculate robust personal daily medians, excluding the target day."""
    target = date.fromisoformat(str(end_date))
    start = target - timedelta(days=window_days)
    daily: dict[str, dict[str, float]] = {}
    for record in records:
        if record.get("status", "completed") != "completed":
            continue
        try:
            record_date = date.fromisoformat(str(record.get("date")))
        except (TypeError, ValueError):
            continue
        if not (start <= record_date < target):
            continue
        summary = record.get("summary") or {}
        bucket = daily.setdefault(record_date.isoformat(), {})
        for metric in BASELINE_METRICS:
            value = summary.get(metric)
            if value is not None:
                bucket[metric] = bucket.get(metric, 0.0) + float(value)

    metric_values = {
        metric: [day[metric] for day in daily.values() if metric in day]
        for metric in BASELINE_METRICS
    }
    sample_days = len(daily)
    return {
        "status": "ready" if sample_days >= min_days else "insufficient_data",
        "window_days": window_days,
        "sample_days": sample_days,
        "metrics": {
            metric: {
                "median": round(float(median(values)), 2) if values else None,
                "days": len(values),
            }
            for metric, values in metric_values.items()
        },
    }
