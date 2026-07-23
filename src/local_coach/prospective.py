"""Prospective Local Coach collection protocol and read-only progress gate."""

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path

from ..db import DB_PATH
from .config import LocalCoachConfigError
from .evaluation import evaluate_longitudinal


BASE_DIR = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = BASE_DIR / "config" / "local_coach_prospective_evaluation.json"


def load_collection_rows(connection, start, current_day):
    try:
        return connection.execute(
            """SELECT date, created_at FROM local_coach_recommendations
               WHERE date >= ? AND date <= ? ORDER BY date""",
            (start, current_day.isoformat()),
        ).fetchall()
    except sqlite3.OperationalError:
        return []


def classify_collection_rows(rows, maximum_delay_days):
    eligible_dates, late_dates = [], []
    for row in rows:
        sample_date = date.fromisoformat(row["date"])
        try:
            generated_date = date.fromisoformat(str(row["created_at"])[:10])
        except (TypeError, ValueError):
            late_dates.append(row["date"])
            continue
        delay = (generated_date - sample_date).days
        if 0 <= delay <= maximum_delay_days:
            eligible_dates.append(row["date"])
        else:
            late_dates.append(row["date"])
    return eligible_dates, late_dates


def load_protocol(path=PROTOCOL_PATH):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalCoachConfigError("Unable to load prospective evaluation protocol") from exc
    required = {
        "protocol_version", "protocol_start_date", "target_unique_days",
        "maximum_generation_delay_days", "require_schema_pass_rate",
        "require_deterministic_match_rate", "require_no_cloud_marker_rate",
        "require_safety_notice_rate",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise LocalCoachConfigError("Prospective protocol fields do not match authority")
    if value["protocol_version"] != "1.0.0":
        raise LocalCoachConfigError("Unsupported prospective protocol version")
    try:
        date.fromisoformat(value["protocol_start_date"])
    except (TypeError, ValueError) as exc:
        raise LocalCoachConfigError("Invalid prospective protocol start date") from exc
    for key in ("target_unique_days", "maximum_generation_delay_days"):
        if not isinstance(value[key], int) or value[key] < (1 if key == "target_unique_days" else 0):
            raise LocalCoachConfigError(f"Invalid prospective protocol value: {key}")
    for key in required:
        if key.startswith("require_") and not isinstance(value[key], (int, float)):
            raise LocalCoachConfigError(f"Invalid prospective protocol rate: {key}")
        if key.startswith("require_") and not 0 <= value[key] <= 1:
            raise LocalCoachConfigError(f"Invalid prospective protocol rate: {key}")
    return value


def evaluate_prospective(connection=None, *, today=None, protocol=None):
    """Report genuine post-protocol progress; never creates or backfills samples."""
    owns_connection = connection is None
    if connection is None:
        connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
    protocol = protocol or load_protocol()
    current_day = today or date.today()
    start = protocol["protocol_start_date"]
    target = protocol["target_unique_days"]
    try:
        rows = load_collection_rows(connection, start, current_day)
        eligible_dates, late_dates = classify_collection_rows(
            rows, protocol["maximum_generation_delay_days"]
        )

        evaluation_config = {
            "evaluation_version": "1.0.0", "minimum_records": target,
            "required_schema_pass_rate": protocol["require_schema_pass_rate"],
            "required_deterministic_match_rate": protocol["require_deterministic_match_rate"],
            "required_no_cloud_marker_rate": protocol["require_no_cloud_marker_rate"],
            "required_safety_notice_rate": protocol["require_safety_notice_rate"],
            "maximum_duplicate_keys": 0,
        }
        base = evaluate_longitudinal(
            connection, date_from=start, date_to=current_day.isoformat(),
            today=current_day, evaluation_config=evaluation_config,
        )
        checks = dict(base["checks"])
        checks["target_unique_days"] = len(set(eligible_dates)) >= target
        checks["timely_generation"] = not late_dates
        success = all(checks.values())
        blockers = [name for name, passed in checks.items() if not passed]
        return {
            "protocol_version": protocol["protocol_version"],
            "protocol_start_date": start, "as_of_date": current_day.isoformat(),
            "status": "passed" if success else "collecting",
            "success": success, "target_unique_days": target,
            "observed_record_count": len(rows), "eligible_unique_days": len(set(eligible_dates)),
            "remaining_unique_days": max(target - len(set(eligible_dates)), 0),
            "late_generation_count": len(late_dates),
            "schema_pass_rate": base["schema_pass_rate"],
            "deterministic_match_rate": base["deterministic_match_rate"],
            "no_cloud_marker_rate": base["no_cloud_marker_rate"],
            "safety_notice_rate": base["safety_notice_rate"],
            "checks": checks, "blockers": blockers,
            "generated_without_cloud_ai": True,
        }
    finally:
        if owns_connection:
            connection.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Track prospective Local Coach evaluation progress read-only.")
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    result = evaluate_prospective()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.require_pass and not result["success"]:
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    main()
