import uuid
from datetime import datetime

from .config import load_source_config, source_priority


def select_primary(rows, config=None):
    config = config or load_source_config()
    eligible = [dict(row) for row in rows if bool(row.get("reviewed"))]
    if not eligible:
        return None, "no_reviewed_source"
    explicit = [row for row in eligible if bool(row.get("selected_as_primary"))]
    candidates = explicit or eligible
    best_priority = min(source_priority(row.get("source_type"), config) for row in candidates)
    candidates = [row for row in candidates if source_priority(row.get("source_type"), config) == best_priority]
    chosen = max(candidates, key=lambda row: (str(row.get("measurement_time") or ""), int(row.get("id") or 0)))
    reason = "user_selected" if explicit else "source_priority_then_measurement_time"
    return chosen, reason


def create_measurement_group(connection, audit_ids, date_value, measurement_times=None,
                             confirmed_by_user=False, config=None):
    if not confirmed_by_user:
        raise ValueError("measurement_group_confirmation_required")
    ids = sorted({int(value) for value in audit_ids})
    if len(ids) < 2:
        raise ValueError("measurement_group_requires_two_screenshots")
    rows = connection.execute(
        f"SELECT id,detected_date,reviewed FROM kubios_screenshot_imports WHERE id IN ({','.join('?' for _ in ids)})",
        ids,
    ).fetchall()
    if len(rows) != len(ids):
        raise ValueError("measurement_group_audit_missing")
    known_dates = {row["detected_date"] for row in rows if row["detected_date"]}
    if known_dates and known_dates != {date_value}:
        raise ValueError("measurement_group_date_mismatch")
    times = [value for value in (measurement_times or []) if value]
    if len(times) >= 2:
        parsed = [datetime.fromisoformat(f"{date_value}T{value}" if "T" not in value else value) for value in times]
        window = (max(parsed) - min(parsed)).total_seconds() / 60
        limit = (config or load_source_config())["measurement_group"]["maximum_time_window_minutes"]
        if window > limit:
            raise ValueError("measurement_group_time_window_exceeded")
    group_id = str(uuid.uuid4())
    connection.execute(
        "INSERT INTO kubios_measurement_groups(id,date,measurement_time_start,measurement_time_end,confirmed_by_user,confirmation_reason) VALUES (?,?,?,?,1,?)",
        (group_id, date_value, min(times) if times else None, max(times) if times else None, "explicit_user_confirmation"),
    )
    connection.execute(
        f"UPDATE kubios_screenshot_imports SET measurement_group_id=? WHERE id IN ({','.join('?' for _ in ids)})",
        (group_id, *ids),
    )
    hashes = [row[0] for row in connection.execute(
        f"SELECT file_sha256 FROM kubios_screenshot_imports WHERE id IN ({','.join('?' for _ in ids)})", ids
    ).fetchall()]
    if hashes:
        connection.execute(
            f"UPDATE kubios_hrv_measurements_raw SET measurement_group_id=? WHERE source_file_sha256 IN ({','.join('?' for _ in hashes)})",
            (group_id, *hashes),
        )
    connection.commit()
    return group_id
