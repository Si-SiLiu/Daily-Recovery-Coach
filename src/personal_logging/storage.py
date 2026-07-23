"""The sole parameterized SQLite write boundary for personal logging."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable

from .validation import validate_body, validate_nutrition, validate_session, validate_set


def _insert(connection: sqlite3.Connection, table: str, data: dict[str, Any]) -> int:
    columns = tuple(data)
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    cursor = connection.execute(sql, tuple(data[column] for column in columns))
    connection.commit()
    return int(cursor.lastrowid)


def _update(connection: sqlite3.Connection, table: str, record_id: int, data: dict[str, Any]) -> bool:
    if not data:
        return False
    assignments = ", ".join(f"{column} = ?" for column in data)
    cursor = connection.execute(
        f"UPDATE {table} SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*data.values(), record_id),
    )
    connection.commit()
    return cursor.rowcount > 0


def _delete(connection: sqlite3.Connection, table: str, record_id: int) -> bool:
    cursor = connection.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
    connection.commit()
    return cursor.rowcount > 0


def create_body_measurement(connection: sqlite3.Connection, data: dict[str, Any]) -> int:
    data = dict(validate_body(dict(data)))
    if data.get("height_cm") is None:
        row = connection.execute(
            "SELECT height_cm FROM body_measurements WHERE height_cm IS NOT NULL ORDER BY date DESC, id DESC LIMIT 1"
        ).fetchone()
        if not row:
            raise ValueError("HEIGHT_REQUIRED_FOR_FIRST_MEASUREMENT")
        data["height_cm"] = row[0]
    if data.get("is_primary"):
        connection.execute("UPDATE body_measurements SET is_primary = 0 WHERE date = ?", (data["date"],))
    data["is_primary"] = int(bool(data.get("is_primary")))
    return _insert(connection, "body_measurements", data)


def update_body_measurement(connection: sqlite3.Connection, record_id: int, data: dict[str, Any]) -> bool:
    existing = connection.execute("SELECT * FROM body_measurements WHERE id = ?", (record_id,)).fetchone()
    if not existing:
        return False
    merged = {**dict(existing), **data}
    validate_body(merged)
    allowed = {key: value for key, value in data.items() if key in {
        "date", "measurement_time", "height_cm", "weight_kg", "waist_cm",
        "body_fat_percent", "is_primary", "notes",
    }}
    if allowed.get("is_primary"):
        connection.execute("UPDATE body_measurements SET is_primary = 0 WHERE date = ?", (merged["date"],))
    if "is_primary" in allowed:
        allowed["is_primary"] = int(bool(allowed["is_primary"]))
    return _update(connection, "body_measurements", record_id, allowed)


def delete_body_measurement(connection: sqlite3.Connection, record_id: int) -> bool:
    return _delete(connection, "body_measurements", record_id)


def list_body_measurements(connection: sqlite3.Connection, limit: int = 90) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM body_measurements ORDER BY date DESC, is_primary DESC, id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def create_nutrition_log(connection: sqlite3.Connection, data: dict[str, Any]) -> int:
    return _insert(connection, "nutrition_logs", validate_nutrition(dict(data)))


def update_nutrition_log(connection: sqlite3.Connection, record_id: int, data: dict[str, Any]) -> bool:
    existing = connection.execute("SELECT * FROM nutrition_logs WHERE id = ?", (record_id,)).fetchone()
    if not existing:
        return False
    merged = {**dict(existing), **data}
    validate_nutrition(merged)
    allowed = {key: value for key, value in data.items() if key not in {"id", "created_at", "updated_at"}}
    return _update(connection, "nutrition_logs", record_id, allowed)


def delete_nutrition_log(connection: sqlite3.Connection, record_id: int) -> bool:
    return _delete(connection, "nutrition_logs", record_id)


def list_nutrition_logs(connection: sqlite3.Connection, log_date: str | None = None) -> list[dict[str, Any]]:
    if log_date:
        rows = connection.execute("SELECT * FROM nutrition_logs WHERE date = ? ORDER BY meal_time, id", (log_date,)).fetchall()
    else:
        rows = connection.execute("SELECT * FROM nutrition_logs ORDER BY date DESC, meal_time DESC, id DESC").fetchall()
    return [dict(row) for row in rows]


def save_nutrition_template(connection: sqlite3.Connection, name: str, items: Iterable[dict[str, Any]]) -> int:
    payload = json.dumps(list(items), ensure_ascii=False, sort_keys=True)
    connection.execute(
        "INSERT INTO nutrition_templates(name, items_json) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET items_json=excluded.items_json, updated_at=CURRENT_TIMESTAMP",
        (name, payload),
    )
    connection.commit()
    row = connection.execute("SELECT id FROM nutrition_templates WHERE name = ?", (name,)).fetchone()
    return int(row[0])


def copy_nutrition_date(connection: sqlite3.Connection, source_date: str, target_date: str) -> int:
    rows = list_nutrition_logs(connection, source_date)
    count = 0
    for row in rows:
        data = {key: value for key, value in row.items() if key not in {"id", "created_at", "updated_at"}}
        data.update(date=target_date, data_source="template")
        create_nutrition_log(connection, data)
        count += 1
    return count


def add_from_nutrition_template(connection: sqlite3.Connection, template_id: int, target_date: str) -> int:
    row = connection.execute("SELECT items_json FROM nutrition_templates WHERE id = ?", (template_id,)).fetchone()
    if not row:
        raise ValueError("NUTRITION_TEMPLATE_NOT_FOUND")
    count = 0
    for item in json.loads(row[0]):
        item.update(date=target_date, data_source="template")
        create_nutrition_log(connection, item)
        count += 1
    return count


def create_workout_session(connection: sqlite3.Connection, data: dict[str, Any]) -> int:
    data = dict(validate_session(dict(data)))
    data["metadata_json"] = json.dumps(data.pop("metadata", {}) or {}, ensure_ascii=False, sort_keys=True)
    return _insert(connection, "workout_sessions", data)


def update_workout_session(connection: sqlite3.Connection, record_id: int, data: dict[str, Any]) -> bool:
    existing = connection.execute("SELECT * FROM workout_sessions WHERE id = ?", (record_id,)).fetchone()
    if not existing:
        return False
    candidate = dict(data)
    if "metadata" in candidate:
        candidate["metadata_json"] = json.dumps(candidate.pop("metadata") or {}, ensure_ascii=False, sort_keys=True)
    merged = {**dict(existing), **candidate}
    validate_session(merged)
    return _update(connection, "workout_sessions", record_id, candidate)


def delete_workout_session(connection: sqlite3.Connection, record_id: int) -> bool:
    connection.execute("PRAGMA foreign_keys = ON")
    return _delete(connection, "workout_sessions", record_id)


def list_workout_sessions(connection: sqlite3.Connection, log_date: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM workout_sessions"
    params: tuple[Any, ...] = ()
    if log_date:
        query += " WHERE date = ?"
        params = (log_date,)
    rows = connection.execute(query + " ORDER BY date DESC, start_time DESC, id DESC", params).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
        result.append(item)
    return result


def create_exercise_set(connection: sqlite3.Connection, session_id: int, data: dict[str, Any]) -> int:
    data = dict(validate_set(dict(data)))
    data["workout_session_id"] = session_id
    return _insert(connection, "exercise_sets", data)


def create_batch_sets(connection: sqlite3.Connection, session_id: int, exercise_name: str,
                      sets: int, reps: int | None = None, weight_kg: float | None = None,
                      **extra: Any) -> list[int]:
    if sets <= 0:
        raise ValueError("INVALID_SET_COUNT")
    return [create_exercise_set(connection, session_id, {
        "exercise_name": exercise_name, "set_number": number,
        "reps": reps, "weight_kg": weight_kg, **extra,
    }) for number in range(1, sets + 1)]


def update_exercise_set(connection: sqlite3.Connection, record_id: int, data: dict[str, Any]) -> bool:
    existing = connection.execute("SELECT * FROM exercise_sets WHERE id = ?", (record_id,)).fetchone()
    if not existing:
        return False
    validate_set({**dict(existing), **data})
    return _update(connection, "exercise_sets", record_id, data)


def delete_exercise_set(connection: sqlite3.Connection, record_id: int) -> bool:
    return _delete(connection, "exercise_sets", record_id)


def list_exercise_sets(connection: sqlite3.Connection, session_id: int) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(
        "SELECT * FROM exercise_sets WHERE workout_session_id = ? ORDER BY set_number, id", (session_id,)
    ).fetchall()]


def create_session_link(connection: sqlite3.Connection, polar_external_id: str, session_id: int,
                        match_method: str, confidence: float | None = None,
                        confirmed_by_user: bool = False) -> int:
    if match_method != "manual" and confirmed_by_user:
        raise ValueError("AUTOMATIC_LINK_CANNOT_AUTO_CONFIRM")
    return _insert(connection, "polar_manual_session_links", {
        "polar_session_external_id": polar_external_id,
        "workout_session_id": session_id,
        "match_method": match_method,
        "confidence": confidence,
        "confirmed_by_user": int(confirmed_by_user),
    })
