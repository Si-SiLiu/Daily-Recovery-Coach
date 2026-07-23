"""Parameterized SQLite CRUD for manual activity, sleep, and recovery logs."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, is_dataclass
from typing import Any, Callable

from .validation import validate_activity, validate_recovery, validate_sleep


ACTIVITY_FIELDS = {
    "date", "start_time", "end_time", "duration_minutes", "activity_type",
    "activity_name", "average_hr_bpm", "max_hr_bpm", "calories_kcal",
    "fat_burn_percentage", "distance_m", "session_rpe", "notes",
    "linked_polar_session_id", "confirmed_by_user",
}
SLEEP_FIELDS = {
    "sleep_date", "bed_time", "sleep_start_time", "wake_time", "get_up_time",
    "sleep_duration_minutes", "nap_duration_minutes", "subjective_sleep_quality",
    "awakenings", "notes", "total_sleep_duration_minutes",
    "actual_sleep_duration_minutes", "deep_sleep_duration_minutes",
    "rem_sleep_duration_minutes", "average_sleep_hr_bpm",
    "minimum_sleep_hr_bpm", "nightly_hrv_rmssd", "respiration_rate",
}
RECOVERY_FIELDS = {
    "date", "measurement_time", "subjective_recovery", "fatigue",
    "muscle_soreness", "mental_energy", "training_motivation", "stress_level",
    "pain_present", "pain_location", "notes", "morning_rmssd_ms",
    "morning_resting_hr_bpm",
}


def _mapping(data: Any) -> dict[str, Any]:
    if is_dataclass(data):
        return asdict(data)
    if isinstance(data, dict):
        return dict(data)
    raise TypeError("MANUAL_LOG_DATA_MUST_BE_MAPPING_OR_DATACLASS")


def _filtered(data: Any, allowed: set[str]) -> dict[str, Any]:
    values = _mapping(data)
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(f"UNKNOWN_MANUAL_LOG_FIELDS:{','.join(sorted(unknown))}")
    return values


def _row_dict(cursor: sqlite3.Cursor, row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return dict(row)
    return dict(zip((column[0] for column in cursor.description), row))


def _get(connection: sqlite3.Connection, table: str, record_id: int) -> dict[str, Any] | None:
    cursor = connection.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,))
    return _row_dict(cursor, cursor.fetchone())


def _create(
    connection: sqlite3.Connection,
    table: str,
    data: Any,
    allowed: set[str],
    validator: Callable[[dict[str, Any]], dict[str, Any]],
) -> int:
    values = validator(_filtered(data, allowed))
    columns = tuple(values)
    placeholders = ", ".join("?" for _ in columns)
    cursor = connection.execute(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        tuple(values[column] for column in columns),
    )
    connection.commit()
    return int(cursor.lastrowid)


def _update(
    connection: sqlite3.Connection,
    table: str,
    record_id: int,
    data: Any,
    allowed: set[str],
    validator: Callable[[dict[str, Any]], dict[str, Any]],
) -> bool:
    existing = _get(connection, table, record_id)
    if existing is None:
        return False
    changes = _filtered(data, allowed)
    if not changes:
        return False
    validator({**existing, **changes})
    assignments = ", ".join(f"{column} = ?" for column in changes)
    cursor = connection.execute(
        f"UPDATE {table} SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*changes.values(), record_id),
    )
    connection.commit()
    return cursor.rowcount > 0


def _delete(connection: sqlite3.Connection, table: str, record_id: int) -> bool:
    cursor = connection.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
    connection.commit()
    return cursor.rowcount > 0


def _list(
    connection: sqlite3.Connection,
    table: str,
    date_column: str,
    log_date: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    if limit < 1:
        raise ValueError("INVALID_LIST_LIMIT")
    params: tuple[Any, ...]
    if log_date is None:
        query = f"SELECT * FROM {table} ORDER BY {date_column} DESC, id DESC LIMIT ?"
        params = (limit,)
    else:
        query = (
            f"SELECT * FROM {table} WHERE {date_column} = ? "
            f"ORDER BY id DESC LIMIT ?"
        )
        params = (log_date, limit)
    cursor = connection.execute(query, params)
    return [_row_dict(cursor, row) for row in cursor.fetchall()]


def create_activity_session(connection: sqlite3.Connection, data: Any) -> int:
    values = _filtered(data, ACTIVITY_FIELDS)
    if "confirmed_by_user" in values:
        values["confirmed_by_user"] = int(bool(values["confirmed_by_user"]))
    return _create(connection, "manual_activity_sessions", values, ACTIVITY_FIELDS, validate_activity)


def update_activity_session(connection: sqlite3.Connection, record_id: int, data: Any) -> bool:
    values = _filtered(data, ACTIVITY_FIELDS)
    if "confirmed_by_user" in values:
        values["confirmed_by_user"] = int(bool(values["confirmed_by_user"]))
    return _update(connection, "manual_activity_sessions", record_id, values, ACTIVITY_FIELDS, validate_activity)


def delete_activity_session(connection: sqlite3.Connection, record_id: int) -> bool:
    return _delete(connection, "manual_activity_sessions", record_id)


def get_activity_session(connection: sqlite3.Connection, record_id: int) -> dict[str, Any] | None:
    return _get(connection, "manual_activity_sessions", record_id)


def list_activity_sessions(
    connection: sqlite3.Connection, log_date: str | None = None, limit: int = 200
) -> list[dict[str, Any]]:
    return _list(connection, "manual_activity_sessions", "date", log_date, limit)


def create_activity_link(
    connection: sqlite3.Connection,
    polar_session_external_id: str,
    manual_activity_session_id: int,
    *,
    match_method: str = "manual",
    match_confidence: float | None = None,
    confirmed_by_user: bool = False,
) -> int:
    if match_method not in {"manual", "date_time", "date_type", "date_duration"}:
        raise ValueError("INVALID_ACTIVITY_LINK_METHOD")
    if match_method != "manual" and confirmed_by_user:
        raise ValueError("AUTOMATIC_LINK_CANNOT_AUTO_CONFIRM")
    if match_confidence is not None and not 0 <= float(match_confidence) <= 1:
        raise ValueError("INVALID_ACTIVITY_LINK_CONFIDENCE")
    cursor = connection.execute(
        """
        INSERT INTO polar_manual_session_links (
            polar_session_external_id,manual_activity_session_id,match_method,
            confidence,match_confidence,confirmed_by_user
        ) VALUES (?,?,?,?,?,?)
        """,
        (
            polar_session_external_id,
            manual_activity_session_id,
            match_method,
            match_confidence,
            match_confidence,
            int(bool(confirmed_by_user)),
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def confirm_activity_link(connection: sqlite3.Connection, link_id: int) -> bool:
    cursor = connection.execute(
        "UPDATE polar_manual_session_links SET confirmed_by_user=1, "
        "updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (link_id,),
    )
    connection.commit()
    return cursor.rowcount > 0


def delete_activity_link(connection: sqlite3.Connection, link_id: int) -> bool:
    return _delete(connection, "polar_manual_session_links", link_id)


def list_activity_links(
    connection: sqlite3.Connection, manual_activity_session_id: int | None = None
) -> list[dict[str, Any]]:
    query = "SELECT * FROM polar_manual_session_links"
    params: tuple[Any, ...] = ()
    if manual_activity_session_id is not None:
        query += " WHERE manual_activity_session_id=?"
        params = (manual_activity_session_id,)
    cursor = connection.execute(query + " ORDER BY id DESC", params)
    return [_row_dict(cursor, row) for row in cursor.fetchall()]


def create_sleep_log(connection: sqlite3.Connection, data: Any) -> int:
    return _create(connection, "manual_sleep_logs", data, SLEEP_FIELDS, validate_sleep)


def update_sleep_log(connection: sqlite3.Connection, record_id: int, data: Any) -> bool:
    return _update(connection, "manual_sleep_logs", record_id, data, SLEEP_FIELDS, validate_sleep)


def delete_sleep_log(connection: sqlite3.Connection, record_id: int) -> bool:
    return _delete(connection, "manual_sleep_logs", record_id)


def get_sleep_log(connection: sqlite3.Connection, record_id: int) -> dict[str, Any] | None:
    return _get(connection, "manual_sleep_logs", record_id)


def list_sleep_logs(
    connection: sqlite3.Connection, sleep_date: str | None = None, limit: int = 200
) -> list[dict[str, Any]]:
    return _list(connection, "manual_sleep_logs", "sleep_date", sleep_date, limit)


def create_recovery_log(connection: sqlite3.Connection, data: Any) -> int:
    values = _filtered(data, RECOVERY_FIELDS)
    if "pain_present" in values:
        values["pain_present"] = int(bool(values["pain_present"]))
    return _create(connection, "manual_recovery_logs", values, RECOVERY_FIELDS, validate_recovery)


def update_recovery_log(connection: sqlite3.Connection, record_id: int, data: Any) -> bool:
    values = _filtered(data, RECOVERY_FIELDS)
    if "pain_present" in values:
        values["pain_present"] = int(bool(values["pain_present"]))
    return _update(connection, "manual_recovery_logs", record_id, values, RECOVERY_FIELDS, validate_recovery)


def delete_recovery_log(connection: sqlite3.Connection, record_id: int) -> bool:
    return _delete(connection, "manual_recovery_logs", record_id)


def get_recovery_log(connection: sqlite3.Connection, record_id: int) -> dict[str, Any] | None:
    return _get(connection, "manual_recovery_logs", record_id)


def list_recovery_logs(
    connection: sqlite3.Connection, log_date: str | None = None, limit: int = 200
) -> list[dict[str, Any]]:
    return _list(connection, "manual_recovery_logs", "date", log_date, limit)


# Explicit aliases make the public API self-documenting at call sites.
create_manual_activity_session = create_activity_session
update_manual_activity_session = update_activity_session
delete_manual_activity_session = delete_activity_session
create_manual_sleep_log = create_sleep_log
update_manual_sleep_log = update_sleep_log
delete_manual_sleep_log = delete_sleep_log
create_manual_recovery_log = create_recovery_log
update_manual_recovery_log = update_recovery_log
delete_manual_recovery_log = delete_recovery_log
