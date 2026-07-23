"""Transactional SQLite storage for meal events and their normalized items."""

from __future__ import annotations

import sqlite3
from typing import Any

from .validation import (
    CATEGORIES,
    CORE_CATEGORIES,
    EXTENDED_CATEGORIES,
    MEAL_TYPES,
    NutritionEventValidationError,
    validate_meal_event,
)
from .analysis import analyze_meal_items
from .supplements import summarize_supplements, validate_supplement


def _clean_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = []
    for item in items:
        name = str(item.get("item_name") or "").strip() or None
        quantity = item.get("quantity")
        if name is None and quantity in (None, ""):
            continue
        cleaned_item = {
            "category": item.get("category"),
            "position": int(item.get("position")),
            "item_name": name,
            "quantity": float(quantity or 0),
            "unit": item.get("unit"),
            "active_amount": None if item.get("active_amount") in (None, "") else float(item["active_amount"]),
            "active_unit": item.get("active_unit") or None,
            "active_component_name": str(item.get("active_component_name") or "").strip() or None,
            "timing": str(item.get("timing") or "").strip() or None,
            "item_notes": str(item.get("item_notes") or "").strip() or None,
        }
        cleaned.append(validate_supplement(cleaned_item) if cleaned_item["category"] == "supplement" else cleaned_item)
    return cleaned


def create_meal_event(
    connection: sqlite3.Connection,
    event: dict[str, Any],
    items: list[dict[str, Any]],
) -> int:
    return save_meal_event(connection, event, items)


def save_meal_event(
    connection: sqlite3.Connection,
    event: dict[str, Any],
    items: list[dict[str, Any]],
    event_id: int | None = None,
) -> int:
    values = {
        "date": str(event.get("date")),
        "meal_type": event.get("meal_type"),
        "actual_meal_time": str(event.get("actual_meal_time")),
        "notes": str(event.get("notes") or "").strip() or None,
    }
    normalized = _clean_items(items)
    validate_meal_event(values, normalized)
    with connection:
        if event_id is None:
            cursor = connection.execute(
                "INSERT INTO meal_events(date,meal_type,actual_meal_time,notes) VALUES(?,?,?,?)",
                tuple(values.values()),
            )
            event_id = int(cursor.lastrowid)
        else:
            cursor = connection.execute(
                "UPDATE meal_events SET date=?,meal_type=?,actual_meal_time=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (*values.values(), event_id),
            )
            if cursor.rowcount == 0:
                raise NutritionEventValidationError("MEAL_EVENT_NOT_FOUND")
            connection.execute("DELETE FROM meal_event_items WHERE meal_event_id=?", (event_id,))
        connection.executemany(
            """INSERT INTO meal_event_items(
                   meal_event_id,category,position,item_name,quantity,unit,
                   active_amount,active_unit,active_component_name,timing,item_notes
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            [(
                event_id, item["category"], item["position"], item["item_name"],
                item["quantity"], item["unit"], item["active_amount"],
                item["active_unit"], item["active_component_name"], item["timing"], item["item_notes"],
            ) for item in normalized],
        )
    return event_id


def delete_meal_event(connection: sqlite3.Connection, event_id: int) -> bool:
    with connection:
        cursor = connection.execute("DELETE FROM meal_events WHERE id=?", (event_id,))
    return cursor.rowcount > 0


def get_meal_event(connection: sqlite3.Connection, event_id: int) -> dict[str, Any] | None:
    row = connection.execute("SELECT * FROM meal_events WHERE id=?", (event_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result["items"] = [dict(item) for item in connection.execute(
        "SELECT * FROM meal_event_items WHERE meal_event_id=? ORDER BY category,position",
        (event_id,),
    ).fetchall()]
    return result


def list_meal_events(
    connection: sqlite3.Connection,
    log_date: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    if limit < 1:
        raise ValueError("INVALID_LIST_LIMIT")
    where = "WHERE e.date=?" if log_date else ""
    params: tuple[Any, ...] = (log_date, limit) if log_date else (limit,)
    rows = connection.execute(
        f"""SELECT e.*,COUNT(i.id) AS item_count
            FROM meal_events e LEFT JOIN meal_event_items i ON i.meal_event_id=e.id
            {where} GROUP BY e.id
            ORDER BY e.date DESC,e.actual_meal_time DESC,e.id DESC LIMIT ?""",
        params,
    ).fetchall()
    records = [dict(row) for row in rows]
    if not records:
        return records
    placeholders = ",".join("?" for _ in records)
    item_rows = connection.execute(
        f"SELECT * FROM meal_event_items WHERE meal_event_id IN ({placeholders}) ORDER BY meal_event_id,category,position",
        tuple(item["id"] for item in records),
    ).fetchall()
    grouped = {item["id"]: [] for item in records}
    for item in item_rows:
        grouped[item["meal_event_id"]].append(dict(item))
    for record in records:
        record.update(analyze_meal_items(grouped[record["id"]]))
        record["supplements"] = summarize_supplements(grouped[record["id"]])
    return records
