"""Exercise catalog repository."""

from __future__ import annotations

import json
import sqlite3
from uuid import uuid4

from .validation import EXERCISE_CATEGORIES, MEASUREMENT_MODES, enum_value, text_value


EXERCISE_CATALOG_VERSION = "1.0.0"
CUSTOM_EXERCISE = "custom"


def _decode(row):
    item = dict(row)
    item["secondary_muscle_groups"] = tuple(
        json.loads(item.pop("secondary_muscle_groups_json") or "[]")
    )
    return item


def list_exercise_catalog(connection: sqlite3.Connection, active_only=True):
    where = "WHERE is_active=1" if active_only else ""
    return [_decode(row) for row in connection.execute(
        f"SELECT * FROM exercise_catalog {where} ORDER BY id"
    ).fetchall()]


def exercise_catalog_by_id(connection: sqlite3.Connection):
    return {item["id"]: item for item in list_exercise_catalog(connection)}


def search_exercise_catalog(connection: sqlite3.Connection, query, limit=30):
    needle = str(query or "").strip().casefold()
    catalog = list_exercise_catalog(connection)
    if not needle:
        return catalog[:limit]
    return [item for item in catalog if any(
        needle in str(value).casefold() for value in (
            item["canonical_name"], item["display_name_zh"], item["display_name_en"]
        )
    )][:limit]


def create_custom_exercise_catalog(connection: sqlite3.Connection, payload: dict) -> int:
    """Persist a user-defined exercise only after an explicit UI choice.

    Dashboard code deliberately calls this service only from the main save action;
    merely typing a custom exercise therefore never mutates the catalog.
    """
    name = text_value(payload.get("custom_exercise_name"))
    if not name:
        raise ValueError("MISSING_CUSTOM_EXERCISE_NAME")
    category = enum_value(
        "exercise_category", payload.get("exercise_category"), EXERCISE_CATEGORIES
    )
    mode = enum_value("measurement_mode", payload.get("measurement_mode"), MEASUREMENT_MODES)
    primary = text_value(payload.get("primary_muscle_group"))
    equipment = text_value(payload.get("equipment"))
    unilateral = 1 if bool(payload.get("is_unilateral")) else 0

    existing = connection.execute(
        """
        SELECT id FROM exercise_catalog
        WHERE lower(display_name_zh)=lower(?)
          AND exercise_category=? AND measurement_mode=?
          AND coalesce(primary_muscle_group,'')=coalesce(?,'')
          AND coalesce(equipment,'')=coalesce(?,'')
          AND is_unilateral=?
        ORDER BY id LIMIT 1
        """,
        (name, category, mode, primary, equipment, unilateral),
    ).fetchone()
    if existing:
        return int(existing["id"])

    cursor = connection.execute(
        """
        INSERT INTO exercise_catalog (
            canonical_name,display_name_zh,display_name_en,exercise_category,
            movement_pattern,primary_muscle_group,secondary_muscle_groups_json,
            equipment,measurement_mode,is_unilateral,is_active
        ) VALUES (?,?,?,?,?,?,?,?,?,?,1)
        """,
        (
            f"custom_{uuid4().hex}", name, name, category, "skill", primary,
            "[]", equipment, mode, unilateral,
        ),
    )
    return int(cursor.lastrowid)
