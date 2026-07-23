"""Idempotent daily body, nutrition, and manual-training summaries."""

from .body import weight_change
from .nutrition import summarize_nutrition_rows


def build_body_summary(connection, summary_date):
    row = connection.execute(
        "SELECT * FROM body_measurements WHERE date <= ? ORDER BY date DESC, is_primary DESC, id DESC LIMIT 1",
        (summary_date,),
    ).fetchone()
    if not row:
        return {"latest_weight_kg": None, "height_cm": None, "waist_cm": None,
                "body_fat_percent": None, "weight_change_7d": None, "weight_change_30d": None}
    return {"latest_weight_kg": row["weight_kg"], "height_cm": row["height_cm"],
            "waist_cm": row["waist_cm"], "body_fat_percent": row["body_fat_percent"],
            "weight_change_7d": weight_change(connection, 7, summary_date),
            "weight_change_30d": weight_change(connection, 30, summary_date)}


def rebuild_daily_nutrition_summary(connection, summary_date):
    rows = connection.execute("SELECT * FROM nutrition_logs WHERE date = ?", (summary_date,)).fetchall()
    summary = summarize_nutrition_rows(rows)
    fields = ("logged_meals", "calories", "protein_g", "carbohydrate_g", "fat_g",
              "fiber_g", "water_ml", "sodium_mg", "data_completeness")
    connection.execute(
        f"INSERT INTO daily_nutrition_summary(date,{','.join(fields)}) VALUES (?,{','.join('?' for _ in fields)}) "
        f"ON CONFLICT(date) DO UPDATE SET {','.join(f'{x}=excluded.{x}' for x in fields)},updated_at=CURRENT_TIMESTAMP",
        (summary_date, *(summary[field] for field in fields)),
    )
    connection.commit()
    return summary


def rebuild_daily_training_summary(connection, summary_date):
    sessions = connection.execute("SELECT * FROM workout_sessions WHERE date = ?", (summary_date,)).fetchall()
    sets = connection.execute(
        "SELECT e.* FROM exercise_sets e JOIN workout_sessions w ON w.id=e.workout_session_id WHERE w.date=?",
        (summary_date,),
    ).fetchall()
    values = [row["weight_kg"] * row["reps"] for row in sets if row["weight_kg"] is not None and row["reps"] is not None]
    rpe_loads = [row["duration_minutes"] * row["session_rpe"] for row in sessions if row["duration_minutes"] is not None and row["session_rpe"] is not None]
    def duration(kind):
        entries = [row["duration_minutes"] for row in sessions if row["session_type"] == kind and row["duration_minutes"] is not None]
        return round(sum(entries), 2) if entries else None
    summary = {
        "session_count": len(sessions),
        "strength_session_count": sum(row["session_type"] == "strength" for row in sessions),
        "hiphop_session_count": sum(row["session_type"] == "hiphop" for row in sessions),
        "total_duration_minutes": round(sum(row["duration_minutes"] or 0 for row in sessions), 2) if sessions else None,
        "total_sets": len(sets), "total_reps": sum(row["reps"] or 0 for row in sets),
        "total_volume_kg": round(sum(values), 2) if values else None,
        "average_session_rpe": round(sum(row["session_rpe"] for row in sessions if row["session_rpe"] is not None) / sum(row["session_rpe"] is not None for row in sessions), 2) if any(row["session_rpe"] is not None for row in sessions) else None,
        "session_rpe_load": round(sum(rpe_loads), 2) if rpe_loads else None,
        "strength_duration_minutes": duration("strength"), "hiphop_duration_minutes": duration("hiphop"),
        "juggling_duration_minutes": duration("juggling"),
    }
    fields = tuple(summary)
    connection.execute(
        f"INSERT INTO daily_training_summary(date,{','.join(fields)}) VALUES (?,{','.join('?' for _ in fields)}) "
        f"ON CONFLICT(date) DO UPDATE SET {','.join(f'{x}=excluded.{x}' for x in fields)},updated_at=CURRENT_TIMESTAMP",
        (summary_date, *(summary[field] for field in fields)),
    )
    connection.commit()
    return summary


def rebuild_daily_summaries(connection, summary_date):
    return {"date": summary_date, "body": build_body_summary(connection, summary_date),
            "nutrition": rebuild_daily_nutrition_summary(connection, summary_date),
            "training": rebuild_daily_training_summary(connection, summary_date)}
