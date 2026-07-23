"""Rebuild deterministic summaries for locally entered records.

This step deliberately does not feed subjective health logs into the recovery,
baseline, confidence, or local-coach engines.  It only refreshes the existing
nutrition/training summaries and reports how many manual health rows are
available for the separate resolution step.
"""

try:
    from src.db import connect
    from src.personal_logging.summaries import (
        rebuild_daily_nutrition_summary,
        rebuild_daily_training_summary,
    )
except ImportError:  # pragma: no cover - script-mode compatibility
    from db import connect
    from personal_logging.summaries import (
        rebuild_daily_nutrition_summary,
        rebuild_daily_training_summary,
    )


def _dates(connection, table, column="date"):
    try:
        rows = connection.execute(
            f"SELECT DISTINCT {column} AS summary_date FROM {table} "
            f"WHERE {column} IS NOT NULL ORDER BY {column}"
        ).fetchall()
    except Exception:
        return []
    return [row["summary_date"] for row in rows]


def _count(connection, table):
    try:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except Exception:
        return 0


def run(context, dry_run=False):
    if dry_run:
        return {
            "manual_records_read": 0,
            "nutrition_summaries_updated": 0,
            "training_summaries_updated": 0,
        }

    with connect() as connection:
        nutrition_dates = _dates(connection, "nutrition_logs")
        training_dates = _dates(connection, "workout_sessions")
        for summary_date in nutrition_dates:
            rebuild_daily_nutrition_summary(connection, summary_date)
        for summary_date in training_dates:
            rebuild_daily_training_summary(connection, summary_date)
        manual_records = sum(
            _count(connection, table)
            for table in (
                "manual_activity_sessions",
                "manual_sleep_logs",
                "manual_recovery_logs",
            )
        )

    return {
        "manual_records_read": manual_records,
        "nutrition_summaries_updated": len(nutrition_dates),
        "training_summaries_updated": len(training_dates),
    }
