"""Repository and deterministic calculations for versioned supplement products."""

from __future__ import annotations

from datetime import datetime
import sqlite3
from typing import Any
from uuid import uuid4

from .validation import normalize_ingredient, normalize_product


PRODUCT_COLUMNS = (
    "brand_name", "product_name", "product_variant", "display_name_zh",
    "display_name_en", "barcode", "country_or_region", "dosage_form",
    "product_kind", "default_intake_unit", "serving_quantity", "serving_unit",
    "package_size", "formula_version", "label_version_date",
    "front_label_image_path", "facts_label_image_path", "product_url",
    "data_source", "primary_source_reference", "primary_source_type",
    "verification_status", "user_confirmed", "verified_at", "valid_from",
    "valid_to", "supersedes_product_id", "formula_hash", "label_hash",
)


def _uuid() -> str:
    return str(uuid4())


def _project_product(connection: sqlite3.Connection, row) -> dict[str, Any]:
    item = dict(row)
    item["ingredients"] = [dict(value) for value in connection.execute(
        """SELECT * FROM supplement_product_ingredients
           WHERE supplement_product_id=? AND deleted_at IS NULL ORDER BY id""",
        (item["id"],),
    ).fetchall()]
    item["is_favorite"] = bool(connection.execute(
        "SELECT 1 FROM supplement_product_favorites WHERE supplement_product_id=?",
        (item["id"],),
    ).fetchone())
    return item


def create_product(
    connection: sqlite3.Connection, payload: dict[str, Any],
    ingredients: list[dict[str, Any]] | None = None,
) -> int:
    values = normalize_product(payload)
    cleaned_ingredients = [normalize_ingredient(item) for item in (ingredients or [])]
    with connection:
        cursor = connection.execute(
            f"""INSERT INTO supplement_products(uuid,{','.join(PRODUCT_COLUMNS)})
                VALUES(?,{','.join('?' for _ in PRODUCT_COLUMNS)})""",
            (_uuid(), *(values[name] for name in PRODUCT_COLUMNS)),
        )
        product_id = int(cursor.lastrowid)
        for item in cleaned_ingredients:
            connection.execute(
                """INSERT INTO supplement_product_ingredients(
                       uuid,supplement_product_id,canonical_ingredient_name,
                       display_name_zh,display_name_en,amount_per_serving,
                       amount_unit,serving_quantity,serving_unit,ingredient_role,
                       source_reference,source_type,confidence_level,user_confirmed
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (_uuid(), product_id, *item.values()),
            )
    return product_id


def update_product(connection: sqlite3.Connection, product_id: int, payload: dict[str, Any]) -> None:
    values = normalize_product(payload)
    with connection:
        cursor = connection.execute(
            f"""UPDATE supplement_products SET
                {','.join(f'{name}=?' for name in PRODUCT_COLUMNS)},
                updated_at=CURRENT_TIMESTAMP WHERE id=? AND deleted_at IS NULL""",
            (*(values[name] for name in PRODUCT_COLUMNS), product_id),
        )
    if not cursor.rowcount:
        raise ValueError("SUPPLEMENT_PRODUCT_NOT_FOUND")


def confirm_product(connection: sqlite3.Connection, product_id: int) -> None:
    with connection:
        cursor = connection.execute(
            """UPDATE supplement_products SET verification_status='user_confirmed',
                   user_confirmed=1,verified_at=?,updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND deleted_at IS NULL AND verification_status NOT IN ('rejected','stale')""",
            (datetime.now().astimezone().isoformat(timespec="seconds"), product_id),
        )
    if not cursor.rowcount:
        raise ValueError("SUPPLEMENT_PRODUCT_NOT_CONFIRMABLE")


def get_product(connection: sqlite3.Connection, product_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM supplement_products WHERE id=? AND deleted_at IS NULL", (product_id,)
    ).fetchone()
    return _project_product(connection, row) if row else None


def product_by_id(connection: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    return {item["id"]: item for item in list_products(connection)}


def list_products(connection: sqlite3.Connection, include_medications=True) -> list[dict[str, Any]]:
    kind = "" if include_medications else "AND product_kind!='medication'"
    rows = connection.execute(
        f"""SELECT * FROM supplement_products WHERE deleted_at IS NULL AND is_active=1 {kind}
            ORDER BY COALESCE(brand_name,''),product_name,COALESCE(product_variant,''),id"""
    ).fetchall()
    return [_project_product(connection, row) for row in rows]


def search_local_products(connection: sqlite3.Connection, query: str, limit=20) -> list[dict[str, Any]]:
    term = f"%{str(query or '').strip()}%"
    rows = connection.execute(
        """SELECT * FROM supplement_products WHERE deleted_at IS NULL AND is_active=1
           AND (COALESCE(brand_name,'') LIKE ? OR product_name LIKE ? OR
                COALESCE(product_variant,'') LIKE ? OR COALESCE(barcode,'') LIKE ?)
           ORDER BY user_confirmed DESC,updated_at DESC,id DESC LIMIT ?""",
        (term, term, term, term, int(limit)),
    ).fetchall()
    return [_project_product(connection, row) for row in rows]


def set_product_favorite(connection: sqlite3.Connection, product_id: int, favorite: bool) -> None:
    with connection:
        if favorite:
            connection.execute(
                "INSERT OR IGNORE INTO supplement_product_favorites(supplement_product_id) VALUES(?)",
                (product_id,),
            )
        else:
            connection.execute(
                "DELETE FROM supplement_product_favorites WHERE supplement_product_id=?",
                (product_id,),
            )


def favorite_products(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """SELECT p.* FROM supplement_products p JOIN supplement_product_favorites f
             ON f.supplement_product_id=p.id
           WHERE p.deleted_at IS NULL ORDER BY f.created_at DESC,p.id DESC"""
    ).fetchall()
    return [_project_product(connection, row) for row in rows]


def recent_products(connection: sqlite3.Connection, limit=8) -> list[dict[str, Any]]:
    rows = connection.execute(
        """SELECT p.*,MAX(i.taken_at) AS last_taken_at
           FROM supplement_intake_records i JOIN supplement_products p
             ON p.id=i.supplement_product_id
           WHERE i.deleted_at IS NULL AND p.deleted_at IS NULL
           GROUP BY p.id ORDER BY MAX(i.created_at) DESC,p.id DESC LIMIT ?""",
        (int(limit),),
    ).fetchall()
    return [_project_product(connection, row) for row in rows]


def calculate_intake_ingredients(
    connection: sqlite3.Connection, product_id: int, quantity: object, unit: str,
) -> list[dict[str, Any]] | None:
    product = get_product(connection, product_id)
    if not product or product["product_kind"] == "medication":
        return None
    if product["verification_status"] not in {"user_confirmed", "label_verified", "source_verified"}:
        return None
    if product["verification_status"] == "stale" or unit != product["serving_unit"]:
        return None
    try:
        factor = float(quantity) / float(product["serving_quantity"])
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    if factor <= 0:
        return None
    return [
        {
            "name": item["canonical_ingredient_name"],
            "amount": round(float(item["amount_per_serving"]) * factor, 6),
            "unit": item["amount_unit"],
            "role": item["ingredient_role"],
        }
        for item in product["ingredients"]
        if item["ingredient_role"] in {"active", "nutrient"}
    ]


def soft_delete_product(connection: sqlite3.Connection, product_id: int) -> bool:
    with connection:
        cursor = connection.execute(
            """UPDATE supplement_products SET deleted_at=CURRENT_TIMESTAMP,is_active=0,
                   updated_at=CURRENT_TIMESTAMP WHERE id=? AND deleted_at IS NULL""",
            (product_id,),
        )
    return cursor.rowcount > 0
