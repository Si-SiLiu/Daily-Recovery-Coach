"""Training-load status and robust training-day baselines.

This module is deliberately independent from Streamlit.  It treats Polar's
training-session table as an observation source and keeps the distinctions
between missing, unsynced, incomplete, no-training, and real zero values.
"""

from __future__ import annotations

import json
import math
import sqlite3
import statistics
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterable

from .dashboard_data import DB_PATH
from .pipeline.history import HISTORY_PATH


TRAINING_BASELINE_VERSION = "1.0.0"
TRAINING_STATUS = {
    "not_synced", "syncing", "sync_error", "missing", "partial",
    "no_training_yet", "planned_rest", "confirmed_no_training",
    "training_present", "invalid",
}
MATURITY_THRESHOLDS = (
    (5, "provisional"),
    (10, "reliable"),
    (20, "stable"),
)
CALCULATION_WINDOW_DAYS = 28
WEEK_WINDOW_DAYS = 7
DISTRIBUTION_WINDOW_DAYS = 14


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _duration_seconds(value):
    if value in (None, ""):
        return None
    number = _number(value)
    if number is not None:
        return number
    text = str(value).strip().upper()
    if text.endswith("S") and not text.startswith("P"):
        return _number(text[:-1])
    if not text.startswith("P"):
        return None
    try:
        days = hours = minutes = seconds = 0.0
        body = text[1:]
        if "T" in body:
            day_body, time_body = body.split("T", 1)
        else:
            day_body, time_body = body, ""
        if day_body.endswith("D"):
            days = float(day_body[:-1] or 0)
        current = ""
        for char in time_body:
            if char.isdigit() or char == ".":
                current += char
            elif char == "H":
                hours = float(current or 0); current = ""
            elif char == "M":
                minutes = float(current or 0); current = ""
            elif char == "S":
                seconds = float(current or 0); current = ""
        return days * 86400 + hours * 3600 + minutes * 60 + seconds
    except (TypeError, ValueError):
        return None


def _parse_date(value):
    return date.fromisoformat(str(value)[:10]) if value else None


def _parse_datetime(value):
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    except ValueError:
        return None


def _raw_json(value):
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def maturity_for_count(valid_days: int) -> dict:
    valid_days = max(int(valid_days or 0), 0)
    if valid_days < 5:
        phase, next_threshold = "collecting", 5
    elif valid_days < 10:
        phase, next_threshold = "provisional", 10
    elif valid_days < 20:
        phase, next_threshold = "reliable", 20
    else:
        phase, next_threshold = "stable", None
    return {
        "status": phase,
        "valid_days": valid_days,
        "next_threshold": next_threshold,
        "days_to_next": max(next_threshold - valid_days, 0) if next_threshold else 0,
    }


def _quartiles(values: list[float]):
    if not values:
        return None, None
    if len(values) == 1:
        return values[0], values[0]
    try:
        q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    except statistics.StatisticsError:
        q1 = q3 = values[0]
    return q1, q3


def _metric_baseline(values: Iterable[float], metric: str) -> dict:
    clean = sorted(float(value) for value in values if _number(value) is not None and float(value) >= 0)
    maturity = maturity_for_count(len(clean))
    if not clean:
        return {
            "metric": metric, "center": None, "lower_bound": None, "upper_bound": None,
            "valid_days": 0, "maturity": maturity, "method": "median_iqr",
        }
    lower, upper = _quartiles(clean)
    return {
        "metric": metric,
        "center": statistics.median(clean),
        "lower_bound": lower,
        "upper_bound": upper,
        "valid_days": len(clean),
        "maturity": maturity,
        "method": "median_iqr",
    }


def classify_comparison(value, baseline: dict) -> str:
    if value is None or baseline.get("center") is None:
        return "data_accumulating"
    lower, upper = baseline.get("lower_bound"), baseline.get("upper_bound")
    if lower is None or upper is None:
        return "near_typical"
    spread = max(float(upper) - float(lower), 0.0)
    if value < lower:
        return "markedly_low" if spread == 0 or value < lower - spread / 2 else "slightly_low"
    if value > upper:
        return "markedly_high" if spread == 0 or value > upper + spread / 2 else "slightly_high"
    return "near_typical"


def percent_difference(value, center):
    if value is None or center in (None, 0):
        return None
    return (float(value) - float(center)) / abs(float(center)) * 100


def _sync_context(history_path=HISTORY_PATH):
    path = Path(history_path)
    if not path.exists():
        return {"status": "not_synced", "last_synced_at": None}
    try:
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """SELECT finish_time,success FROM sync_history
               WHERE step='pipeline' ORDER BY id DESC LIMIT 1"""
        ).fetchone()
        connection.close()
    except sqlite3.Error:
        return {"status": "not_synced", "last_synced_at": None}
    if not row:
        return {"status": "not_synced", "last_synced_at": None}
    return {
        "status": "ok" if row["success"] else "sync_error",
        "last_synced_at": row["finish_time"],
    }


def _empty_day(day: date, *, sync_context, is_day_complete, planned_rest=False):
    return {
        "date": day.isoformat(), "status": "missing", "session_count": 0,
        "total_duration_minutes": None, "total_training_calories_kcal": None,
        "last_synced_at": sync_context.get("last_synced_at"),
        "sync_status": sync_context.get("status"), "is_day_complete": is_day_complete,
        "is_planned_rest_day": planned_rest, "data_completeness": 0,
        "status_message": "训练数据缺失", "comparison_allowed": False,
        "duration_field_complete": False, "calories_field_complete": False,
        "raw_session_count": 0,
    }


def _day_record(day: date, rows, *, sync_context, is_day_complete, planned_rest=False,
                observed=False, current_day=None):
    result = _empty_day(day, sync_context=sync_context, is_day_complete=is_day_complete, planned_rest=planned_rest)
    sync_status = sync_context.get("status")
    synced_at = _parse_datetime(sync_context.get("last_synced_at"))
    current_day_not_synced = (
        day == current_day and sync_status == "ok"
        and (synced_at is None or synced_at.astimezone().date() != day)
    )
    if not rows:
        if sync_status == "sync_error":
            result.update(status="sync_error", status_message="训练数据同步失败")
        elif sync_status == "not_synced" or current_day_not_synced:
            result.update(status="not_synced", status_message="尚未同步 Polar 训练数据")
        elif not observed and day != current_day:
            result.update(status="missing", status_message="训练数据缺失")
        elif planned_rest:
            result.update(status="planned_rest", status_message="计划休息日")
        elif not is_day_complete:
            result.update(status="no_training_yet", status_message="今日尚未训练")
        else:
            result.update(status="confirmed_no_training", status_message="今日无训练记录")
        return result

    duration_values = []
    calorie_values = []
    valid_sessions = 0
    for row in rows:
        duration = _duration_seconds(row["duration"]) if "duration" in row.keys() else None
        calories = _number(row["calories"]) if "calories" in row.keys() else None
        duration_valid = duration is not None and duration > 0
        calories_valid = calories is not None and calories >= 0
        if duration_valid:
            duration_values.append(duration / 60)
        if calories_valid:
            calorie_values.append(calories)
        if duration_valid or calories_valid or row["sport"] or row["start_time"]:
            valid_sessions += 1
    result.update(
        status="training_present" if valid_sessions else "invalid",
        status_message="已有有效训练" if valid_sessions else "训练数据异常",
        session_count=valid_sessions,
        raw_session_count=len(rows),
        total_duration_minutes=sum(duration_values) if duration_values else None,
        total_training_calories_kcal=sum(calorie_values) if calorie_values else None,
        duration_field_complete=bool(duration_values),
        calories_field_complete=bool(calorie_values),
        data_completeness=round((bool(duration_values) + bool(calorie_values)) / 2 * 100),
        comparison_allowed=bool(valid_sessions),
    )
    if sync_status == "sync_error":
        result.update(status="sync_error", status_message="训练数据同步失败", comparison_allowed=False)
    elif current_day_not_synced:
        result.update(status="not_synced", status_message="尚未同步 Polar 训练数据", comparison_allowed=False)
    elif day == current_day and not is_day_complete and valid_sessions:
        result.update(status="partial", status_message="今日训练数据仍可能更新", comparison_allowed=False)
    return result


def load_training_days(connection, start_date: date, end_date: date, *, now=None,
                       planned_rest_dates=(), sync_context=None):
    """Return one normalized day object per date, preserving missing values."""
    now = now or datetime.now().astimezone()
    planned = {str(day)[:10] for day in planned_rest_dates}
    sync_context = sync_context or _sync_context()
    rows = connection.execute(
        """SELECT date,external_id,sport,start_time,duration,calories,raw_json
           FROM polar_training_sessions_raw WHERE date>=? AND date<=?
           ORDER BY date,start_time,id""",
        (start_date.isoformat(), end_date.isoformat()),
    ).fetchall()
    try:
        known_dates = {
            row[0] for row in connection.execute(
                "SELECT date FROM daily_recovery_metrics WHERE date>=? AND date<=?",
                (start_date.isoformat(), end_date.isoformat()),
            ).fetchall()
        }
    except sqlite3.OperationalError:
        known_dates = set()
    grouped = defaultdict(list)
    seen = set()
    for row in rows:
        key = (row["external_id"], row["date"])
        if key in seen:
            continue
        seen.add(key)
        grouped[row["date"]].append(row)
    result = []
    cursor = start_date
    while cursor <= end_date:
        complete = cursor < now.date() or (cursor == now.date() and now.time() >= time(23, 59, 59))
        result.append(_day_record(
            cursor, grouped.get(cursor.isoformat(), []), sync_context=sync_context,
            is_day_complete=complete, planned_rest=cursor.isoformat() in planned,
            observed=cursor.isoformat() in known_dates or cursor.isoformat() in grouped,
            current_day=now.date(),
        ))
        cursor += timedelta(days=1)
    return result


def build_training_baseline_view(connection, target_date=None, *, now=None,
                                 planned_rest_dates=(), sync_context=None):
    now = now or datetime.now().astimezone()
    target = _parse_date(target_date) if target_date else now.date()
    start = target - timedelta(days=CALCULATION_WINDOW_DAYS)
    days = load_training_days(
        connection, start, target, now=now,
        planned_rest_dates=planned_rest_dates, sync_context=sync_context,
    )
    today = next(day for day in days if day["date"] == target.isoformat())
    historical = [day for day in days if day["date"] < target.isoformat()]
    duration_baseline = _metric_baseline(
        [day["total_duration_minutes"] for day in historical if day["duration_field_complete"]],
        "training_duration",
    )
    calorie_baseline = _metric_baseline(
        [day["total_training_calories_kcal"] for day in historical if day["calories_field_complete"]],
        "training_calories",
    )
    for metric, baseline, field in (
        ("training_duration", duration_baseline, "total_duration_minutes"),
        ("training_calories", calorie_baseline, "total_training_calories_kcal"),
    ):
        current = today[field] if today["comparison_allowed"] else None
        baseline["current_value"] = current
        baseline["comparison"] = classify_comparison(current, baseline) if today["comparison_allowed"] else today["status"]
        baseline["percent_difference"] = percent_difference(current, baseline["center"])
    recent_days = [day for day in days if target - timedelta(days=6) <= _parse_date(day["date"]) <= target]
    weekly = {
        "session_count": sum(day["session_count"] for day in recent_days),
        "duration_minutes": sum(day["total_duration_minutes"] or 0 for day in recent_days) or None,
        "calories_kcal": (
            sum(day["total_training_calories_kcal"] or 0 for day in recent_days)
            if any(day["total_training_calories_kcal"] is not None for day in recent_days)
            else None
        ),
        # A failed sync is a source-level warning, not proof that an already
        # observed historical training day is invalid. Keep those days in the
        # seven-day count when their session fields are complete.
        "valid_training_days": sum(
            day["session_count"] > 0
            and day["duration_field_complete"]
            and day["calories_field_complete"]
            and day["is_day_complete"]
            for day in recent_days
        ),
        "data_completeness": round(sum(day["data_completeness"] for day in recent_days) / len(recent_days)) if recent_days else 0,
    }
    weekly_calorie_samples = []
    for anchor_index in range(6, len(historical)):
        window = historical[anchor_index - 6:anchor_index + 1]
        if any(day["status"] == "missing" for day in window):
            continue
        if any(day["total_training_calories_kcal"] is not None for day in window):
            weekly_calorie_samples.append(sum(
                day["total_training_calories_kcal"] or 0 for day in window
            ))
    weekly_calorie_baseline = _metric_baseline(weekly_calorie_samples, "weekly_training_calories")
    weekly["typical_calories_kcal"] = weekly_calorie_baseline["center"]
    weekly["typical_calorie_range"] = (
        weekly_calorie_baseline["lower_bound"], weekly_calorie_baseline["upper_bound"]
    ) if weekly_calorie_baseline["center"] is not None else None
    weekly["relative_to_typical"] = percent_difference(
        weekly["calories_kcal"], weekly_calorie_baseline["center"]
    )
    weekly["baseline_valid_weeks"] = weekly_calorie_baseline["valid_days"]
    distribution = []
    for day in days[-DISTRIBUTION_WINDOW_DAYS:]:
        distribution.append({
            "date": day["date"],
            "status": "training" if day["status"] == "training_present" else day["status"],
            "session_count": day["session_count"],
            "duration_minutes": day["total_duration_minutes"],
            "calories_kcal": day["total_training_calories_kcal"],
        })
    return {
        "today": today,
        "days": days,
        "duration_baseline": duration_baseline,
        "calorie_baseline": calorie_baseline,
        "weekly_load": weekly,
        "distribution_14d": distribution,
        "data_quality": {
            "duration_valid_days": duration_baseline["valid_days"],
            "calorie_valid_days": calorie_baseline["valid_days"],
        },
        "calorie_note": "训练热量已包含在 Polar 每日总消耗中，不重复相加。",
    }


def get_training_baseline_view(db_path=DB_PATH, target_date=None, *, now=None,
                               planned_rest_dates=(), sync_context=None):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        return build_training_baseline_view(
            connection, target_date, now=now,
            planned_rest_dates=planned_rest_dates, sync_context=sync_context,
        )
    finally:
        connection.close()
