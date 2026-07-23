"""Food catalog repository, classification, conversion, and nutrition math."""

from __future__ import annotations

import json
import sqlite3

from .food_units import FOOD_UNITS, normalize_food_unit, positive_food_quantity


CUSTOM_FOOD = "custom"
FOOD_CATALOG_VERSION = "1.1.0"
NUTRIENT_COLUMNS = (
    "calories_kcal", "protein_g", "carbohydrate_g", "fat_g", "fiber_g",
    "water_ml", "caffeine_mg", "alcohol_g",
)
PER_100G_COLUMNS = {
    "calories_kcal": "calories_per_100g",
    "protein_g": "protein_per_100g",
    "carbohydrate_g": "carbohydrate_per_100g",
    "fat_g": "fat_per_100g",
    "fiber_g": "fiber_per_100g",
    "water_ml": "water_per_100g",
    "caffeine_mg": "caffeine_per_100g",
    "alcohol_g": "alcohol_per_100g",
}


def _decode(row) -> dict:
    item = dict(row)
    for source, target in (
        ("aliases_json", "aliases"),
        ("allowed_units_json", "allowed_units"),
        ("category_tags_json", "category_tags"),
    ):
        item[target] = tuple(json.loads(item[source]))
    return item


def list_food_catalog(connection: sqlite3.Connection, active_only=True) -> list[dict]:
    where = "WHERE is_active=1" if active_only else ""
    return [_decode(row) for row in connection.execute(
        f"SELECT * FROM food_catalog {where} ORDER BY id"
    ).fetchall()]


def food_catalog_by_id(connection: sqlite3.Connection) -> dict[int, dict]:
    return {item["id"]: item for item in list_food_catalog(connection)}


def food_catalog_by_name(connection: sqlite3.Connection) -> dict[str, dict]:
    return {item["canonical_name"]: item for item in list_food_catalog(connection)}


def search_food_catalog(connection: sqlite3.Connection, query: str, limit=20) -> list[dict]:
    needle = str(query or "").strip().casefold()
    items = list_food_catalog(connection)
    if not needle:
        return items[:limit]
    matches = []
    for item in items:
        values = (
            item["canonical_name"], item["display_name_zh"], item["display_name_en"],
            *item["aliases"],
        )
        if any(needle in str(value).casefold() for value in values):
            matches.append(item)
    return matches[:limit]


def allowed_food_units(catalog: dict | None) -> tuple[str, ...]:
    return tuple(catalog["allowed_units"]) if catalog else FOOD_UNITS


def validate_food_unit(catalog: dict | None, unit: object) -> str:
    normalized = normalize_food_unit(unit)
    if catalog and normalized not in allowed_food_units(catalog):
        raise ValueError("FOOD_UNIT_NOT_ALLOWED")
    return normalized


def calculate_food_values(catalog: dict | None, quantity: object, unit: object) -> dict:
    quantity_value = positive_food_quantity(quantity)
    unit_value = validate_food_unit(catalog, unit)
    result = {
        "quantity": quantity_value,
        "unit": unit_value,
        "normalized_weight_g": None,
        "normalized_volume_ml": None,
        **{name: None for name in NUTRIENT_COLUMNS},
    }
    if not catalog:
        return result

    weight = volume = None
    if unit_value == "g":
        weight = quantity_value
    elif unit_value == "kg":
        weight = quantity_value * 1000
    elif unit_value in {"ml", "l"}:
        volume = quantity_value * (1000 if unit_value == "l" else 1)
        if catalog.get("serving_weight_g") and catalog.get("serving_volume_ml"):
            weight = volume * catalog["serving_weight_g"] / catalog["serving_volume_ml"]
    elif unit_value == catalog.get("serving_unit"):
        if catalog.get("serving_weight_g"):
            weight = quantity_value * catalog["serving_weight_g"]
        if catalog.get("serving_volume_ml"):
            volume = quantity_value * catalog["serving_volume_ml"]

    result["normalized_weight_g"] = round(weight, 4) if weight is not None else None
    result["normalized_volume_ml"] = round(volume, 4) if volume is not None else None
    if weight is None:
        return result
    for output, source in PER_100G_COLUMNS.items():
        per_100g = catalog.get(source)
        if per_100g is not None:
            result[output] = round(weight * float(per_100g) / 100, 4)
    return result


def recent_foods(connection: sqlite3.Connection, limit=8) -> list[dict]:
    rows = connection.execute(
        """SELECT i.food_catalog_id,i.custom_food_name,i.item_type,i.quantity,i.unit,i.created_at
           FROM meal_items i JOIN meal_records r ON r.id=i.meal_record_id
           WHERE i.deleted_at IS NULL AND r.deleted_at IS NULL
           ORDER BY i.created_at DESC,i.id DESC LIMIT 100"""
    ).fetchall()
    catalog = food_catalog_by_id(connection)
    seen = set()
    result = []
    for row in rows:
        key = (row["food_catalog_id"], row["custom_food_name"])
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "food_catalog_id": row["food_catalog_id"],
            "custom_food_name": row["custom_food_name"],
            "item_type": row["item_type"],
            "quantity": row["quantity"],
            "unit": row["unit"],
            "catalog": catalog.get(row["food_catalog_id"]),
        })
        if len(result) >= limit:
            break
    return result


def favorite_foods(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        """SELECT f.* FROM food_catalog f JOIN food_favorites x
           ON x.food_catalog_id=f.id WHERE f.is_active=1 ORDER BY x.created_at DESC"""
    ).fetchall()
    return [_decode(row) for row in rows]


def set_food_favorite(connection: sqlite3.Connection, food_catalog_id: int, enabled: bool) -> None:
    with connection:
        if enabled:
            connection.execute(
                "INSERT OR IGNORE INTO food_favorites(food_catalog_id) VALUES(?)",
                (food_catalog_id,),
            )
        else:
            connection.execute(
                "DELETE FROM food_favorites WHERE food_catalog_id=?", (food_catalog_id,)
            )
