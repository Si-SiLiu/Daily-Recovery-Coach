"""Body trend calculations using user-entered measurements only."""

from datetime import date, timedelta
from typing import Any


BMI_NOTICE = "BMI 仅为一般性体重身高指标，不能单独判断健康或身体成分。"


def calculate_bmi(weight_kg: float | None, height_cm: float | None) -> float | None:
    if not weight_kg or not height_cm:
        return None
    return round(weight_kg / ((height_cm / 100) ** 2), 1)


def weight_trend(connection, days: int, as_of_date: str | None = None) -> list[dict[str, Any]]:
    end = date.fromisoformat(as_of_date) if as_of_date else date.today()
    start = end - timedelta(days=days - 1)
    rows = connection.execute(
        """SELECT date, weight_kg, height_cm, waist_cm, body_fat_percent
           FROM body_measurements WHERE date BETWEEN ? AND ?
           ORDER BY date, is_primary DESC, id DESC""",
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    by_date = {}
    for row in rows:
        by_date.setdefault(row["date"], dict(row))
    return list(by_date.values())


def weight_change(connection, days: int, as_of_date: str) -> float | None:
    rows = weight_trend(connection, days + 1, as_of_date)
    if len(rows) < 2:
        return None
    return round(rows[-1]["weight_kg"] - rows[0]["weight_kg"], 2)
