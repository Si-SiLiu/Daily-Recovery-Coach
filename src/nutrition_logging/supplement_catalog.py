"""Built-in catalog policy plus read-only catalog repository."""

from __future__ import annotations

import json

from .units import SUPPLEMENT_UNITS, normalize_unit


CUSTOM_SUPPLEMENT = "custom"
CATALOG_VERSION = "1.0.0"

CATALOG = {
    "creatine_monohydrate": ("g", ("g", "mg", "scoop")),
    "protein_powder": ("g", ("g", "scoop")),
    "fish_oil": ("capsule", ("capsule", "mg")),
    "lutein": ("capsule", ("capsule", "mg")),
    "vitamin_d3": ("capsule", ("capsule", "tablet", "iu", "mcg")),
    "vitamin_d3k2": ("capsule", ("capsule", "tablet", "iu", "mcg")),
    "magnesium": ("tablet", ("tablet", "capsule", "mg")),
    "electrolyte_powder": ("g", ("g", "sachet", "scoop")),
    "caffeine_tablet": ("tablet", ("tablet", "mg")),
    "collagen": ("g", ("g", "scoop")),
}


def default_unit(canonical_name: str) -> str | None:
    entry = CATALOG.get(canonical_name)
    return entry[0] if entry else None


def allowed_units(canonical_name: str) -> tuple[str, ...]:
    if canonical_name == CUSTOM_SUPPLEMENT or canonical_name not in CATALOG:
        return SUPPLEMENT_UNITS
    return CATALOG[canonical_name][1]


def validate_catalog_unit(canonical_name: str, unit: object) -> str:
    normalized = normalize_unit(unit)
    if normalized not in allowed_units(canonical_name):
        raise ValueError("SUPPLEMENT_UNIT_NOT_ALLOWED")
    return normalized


def list_catalog(connection, active_only=True) -> list[dict]:
    where = "WHERE is_active=1" if active_only else ""
    rows = connection.execute(
        f"SELECT * FROM supplement_catalog {where} ORDER BY id"
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["allowed_units"] = tuple(json.loads(item.pop("allowed_units_json")))
        result.append(item)
    return result


def catalog_by_name(connection) -> dict[str, dict]:
    return {item["canonical_name"]: item for item in list_catalog(connection)}
