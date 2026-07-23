"""Read-only daily operations monitor for prospective Local Coach collection."""

import argparse
import json
import sqlite3
from datetime import date, timedelta

from ..db import get_current_db_path
from .prospective import classify_collection_rows, load_collection_rows, load_protocol


def monitor_daily_collection(connection=None, *, today=None, protocol=None):
    owns_connection = connection is None
    if connection is None:
        db_path = get_current_db_path()
        connection = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
    current_day = today or date.today()
    protocol = protocol or load_protocol()
    start_day = date.fromisoformat(protocol["protocol_start_date"])
    try:
        if current_day < start_day:
            return {
                "protocol_version": protocol["protocol_version"],
                "as_of_date": current_day.isoformat(), "status": "protocol_not_started",
                "on_track": True, "today_collected": False,
                "eligible_unique_days": 0, "target_unique_days": protocol["target_unique_days"],
                "remaining_unique_days": protocol["target_unique_days"],
                "overdue_missing_days": 0, "late_generation_count": 0,
                "current_streak_days": 0, "generated_without_cloud_ai": True,
            }
        rows = load_collection_rows(connection, protocol["protocol_start_date"], current_day)
        eligible, late = classify_collection_rows(rows, protocol["maximum_generation_delay_days"])
        eligible_set = set(eligible)
        completed_days = (current_day - start_day).days
        expected_completed = {
            (start_day + timedelta(days=index)).isoformat()
            for index in range(completed_days)
        }
        overdue = len(expected_completed - eligible_set)
        today_collected = current_day.isoformat() in eligible_set
        cursor = current_day if today_collected else current_day - timedelta(days=1)
        streak = 0
        while cursor >= start_day and cursor.isoformat() in eligible_set:
            streak += 1
            cursor -= timedelta(days=1)
        if overdue or late:
            status = "attention_required"
        elif today_collected:
            status = "collected_today"
        else:
            status = "awaiting_today"
        count = len(eligible_set)
        return {
            "protocol_version": protocol["protocol_version"],
            "as_of_date": current_day.isoformat(), "status": status,
            "on_track": overdue == 0 and not late, "today_collected": today_collected,
            "eligible_unique_days": count, "target_unique_days": protocol["target_unique_days"],
            "remaining_unique_days": max(protocol["target_unique_days"] - count, 0),
            "overdue_missing_days": overdue, "late_generation_count": len(late),
            "current_streak_days": streak, "generated_without_cloud_ai": True,
        }
    finally:
        if owns_connection:
            connection.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Monitor daily prospective collection read-only.")
    parser.add_argument("--require-today", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    result = monitor_daily_collection()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.require_today and not result["today_collected"]:
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    main()
