"""Supplement validation, repository projections, summaries, and AI-safe data."""

from __future__ import annotations

from .supplement_catalog import CATALOG, CUSTOM_SUPPLEMENT, validate_catalog_unit
from .units import normalize_unit, positive_finite
from src.supplements import calculate_intake_ingredients


def validate_supplement(item: dict) -> dict:
    name = str(item.get("item_name") or "").strip()
    if not name:
        raise ValueError("SUPPLEMENT_NAME_REQUIRED")
    canonical = name if name in CATALOG else CUSTOM_SUPPLEMENT
    quantity = positive_finite(item.get("quantity"), "supplement_quantity")
    unit = validate_catalog_unit(canonical, item.get("unit"))
    active_amount = item.get("active_amount")
    active_unit = item.get("active_unit")
    if (active_amount in (None, "")) != (active_unit in (None, "")):
        raise ValueError("ACTIVE_AMOUNT_UNIT_PAIR_REQUIRED")
    if active_amount not in (None, ""):
        active_amount = positive_finite(active_amount, "active_amount")
        active_unit = normalize_unit(active_unit)
    else:
        active_amount = active_unit = None
    return {
        **item,
        "item_name": name,
        "quantity": quantity,
        "unit": unit,
        "active_amount": active_amount,
        "active_unit": active_unit,
        "active_component_name": str(item.get("active_component_name") or "").strip() or None,
        "timing": str(item.get("timing") or "").strip() or None,
        "item_notes": str(item.get("item_notes") or "").strip() or None,
    }


def summarize_supplements(items: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], dict] = {}
    for item in items:
        if item.get("category") != "supplement":
            continue
        key = (str(item.get("item_name")), str(item.get("unit")))
        if key not in groups:
            groups[key] = {
                "name": key[0], "quantity": 0.0, "unit": key[1], "record_count": 0,
                "active_amount": item.get("active_amount"),
                "active_unit": item.get("active_unit"),
                "active_component_name": item.get("active_component_name"),
                "item_notes": item.get("item_notes"),
            }
        groups[key]["quantity"] += float(item.get("quantity") or 0)
        groups[key]["record_count"] += 1
        if groups[key]["record_count"] > 1:
            groups[key]["active_amount"] = None
            groups[key]["active_unit"] = None
            if groups[key]["active_component_name"] != item.get("active_component_name"):
                groups[key]["active_component_name"] = None
            if groups[key]["item_notes"] != item.get("item_notes"):
                groups[key]["item_notes"] = None
    return [
        {**value, "quantity": round(value["quantity"], 4)}
        for _, value in sorted(groups.items())
    ]


def supplements_for_date(connection, date_value: str) -> list[dict]:
    rows = connection.execute(
        """SELECT i.id,i.supplement_product_id,i.custom_brand_name,
                  i.custom_product_name,i.quantity,i.unit,i.taken_at,
                  p.brand_name,p.product_name,p.product_variant,
                  p.verification_status,p.user_confirmed,p.product_kind
           FROM supplement_intake_records i
           JOIN meal_records m ON m.id=i.meal_record_id
           LEFT JOIN supplement_products p ON p.id=i.supplement_product_id
           WHERE m.date=? AND m.deleted_at IS NULL AND i.deleted_at IS NULL
           ORDER BY i.taken_at,i.id""",
        (date_value,),
    ).fetchall()
    result = [dict(row) for row in rows]
    legacy = connection.execute(
        """SELECT NULL AS id,NULL AS supplement_product_id,NULL AS custom_brand_name,
                  i.item_name AS custom_product_name,i.quantity,i.unit,
                  e.actual_meal_time AS taken_at,NULL AS brand_name,
                  i.item_name AS product_name,NULL AS product_variant,
                  'unverified' AS verification_status,0 AS user_confirmed,
                  CASE WHEN lower(i.item_name) LIKE '%finasteride%'
                            OR i.item_name LIKE '%非那雄胺%'
                       THEN 'medication' ELSE 'supplement' END AS product_kind
           FROM meal_event_items i JOIN meal_events e ON e.id=i.meal_event_id
           WHERE e.date=? AND i.category='supplement' AND NOT EXISTS(
               SELECT 1 FROM supplement_intake_records n
               WHERE n.legacy_meal_event_item_id=i.id AND n.deleted_at IS NULL
           ) ORDER BY e.actual_meal_time,i.position,i.id""",
        (date_value,),
    ).fetchall()
    result.extend(dict(row) for row in legacy)
    return result


def ai_supplement_summary(connection, date_value: str) -> list[dict]:
    result = []
    for item in supplements_for_date(connection, date_value):
        summary = {
            "brand": item.get("brand_name") or item.get("custom_brand_name"),
            "product": item.get("product_name") or item.get("custom_product_name"),
            "quantity": item["quantity"],
            "unit": item["unit"],
            "verification_status": item["verification_status"],
            "product_kind": item["product_kind"],
        }
        product_id = item.get("supplement_product_id")
        ingredients = calculate_intake_ingredients(
            connection, product_id, item["quantity"], item["unit"]
        ) if product_id else None
        if ingredients is not None:
            summary["ingredients"] = ingredients
        result.append(summary)
    return result
