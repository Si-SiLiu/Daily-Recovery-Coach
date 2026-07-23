"""Strict local validation for supplement products, ingredients and intakes."""

from __future__ import annotations

from datetime import date
import math
import re
from typing import Any

DOSAGE_FORMS = ("powder", "capsule", "softgel", "tablet", "liquid", "sachet", "drop", "other")
SUPPLEMENT_UNITS = ("g", "mg", "mcg", "ml", "capsule", "tablet", "sachet", "scoop", "drop", "iu")
PRODUCT_KINDS = ("supplement", "medication", "medical_food", "other")
VERIFICATION_STATUSES = (
    "unverified", "candidate", "user_confirmed", "label_verified",
    "source_verified", "stale", "rejected",
)
DATA_SOURCES = (
    "manual_minimal", "barcode_database", "official_product_page",
    "manufacturer_label", "label_ocr", "trusted_database",
    "ai_assisted_search", "imported",
)
INGREDIENT_ROLES = ("active", "nutrient", "carrier", "excipient", "other")
INGREDIENT_UNITS = ("g", "mg", "mcg", "ml", "iu")
INGREDIENT_SOURCE_TYPES = (
    "user_label", "official_product_page", "manufacturer_label",
    "trusted_database", "barcode_database", "retailer_page",
    "ai_assisted_search", "manual_minimal", "imported",
)
CONFIDENCE_LEVELS = ("unknown", "low", "medium", "high", "verified")
BARCODE_RE = re.compile(r"^[0-9]{8,14}$")


def _text(value: object) -> str | None:
    return str(value or "").strip() or None


def _positive(value: object, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_{field.upper()}") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"INVALID_{field.upper()}")
    return number


def normalize_unit(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in SUPPLEMENT_UNITS:
        raise ValueError("INVALID_SUPPLEMENT_UNIT")
    return normalized


def normalize_barcode(value: object) -> str | None:
    barcode = _text(value)
    if barcode is None:
        return None
    compact = barcode.replace(" ", "").replace("-", "")
    if not BARCODE_RE.fullmatch(compact):
        raise ValueError("INVALID_BARCODE")
    return compact


def infer_product_kind(product_name: object, requested: object = None) -> str:
    name = str(product_name or "").strip().lower()
    if "finasteride" in name or "非那雄胺" in name:
        return "medication"
    kind = str(requested or "supplement")
    if kind not in PRODUCT_KINDS:
        raise ValueError("INVALID_PRODUCT_KIND")
    return kind


def normalize_product(payload: dict[str, Any]) -> dict[str, Any]:
    product_name = _text(payload.get("product_name"))
    if not product_name:
        raise ValueError("PRODUCT_NAME_REQUIRED")
    dosage_form = str(payload.get("dosage_form") or "other")
    if dosage_form not in DOSAGE_FORMS:
        raise ValueError("INVALID_DOSAGE_FORM")
    default_unit = normalize_unit(payload.get("default_intake_unit") or payload.get("serving_unit"))
    serving_unit = normalize_unit(payload.get("serving_unit") or default_unit)
    source = str(payload.get("data_source") or "manual_minimal")
    if source not in DATA_SOURCES:
        raise ValueError("INVALID_PRODUCT_DATA_SOURCE")
    status = str(payload.get("verification_status") or "unverified")
    if status not in VERIFICATION_STATUSES:
        raise ValueError("INVALID_VERIFICATION_STATUS")
    source_reference = _text(payload.get("primary_source_reference"))
    if status == "source_verified" and not source_reference:
        raise ValueError("VERIFIED_PRODUCT_SOURCE_REQUIRED")
    user_confirmed = bool(payload.get("user_confirmed"))
    verified_at = _text(payload.get("verified_at"))
    if user_confirmed and not verified_at:
        raise ValueError("PRODUCT_CONFIRMATION_TIME_REQUIRED")
    label_date = _text(payload.get("label_version_date"))
    if label_date:
        try:
            label_date = date.fromisoformat(label_date).isoformat()
        except ValueError as exc:
            raise ValueError("INVALID_LABEL_VERSION_DATE") from exc
    return {
        "brand_name": _text(payload.get("brand_name")),
        "product_name": product_name,
        "product_variant": _text(payload.get("product_variant")),
        "display_name_zh": _text(payload.get("display_name_zh")),
        "display_name_en": _text(payload.get("display_name_en")),
        "barcode": normalize_barcode(payload.get("barcode")),
        "country_or_region": _text(payload.get("country_or_region")),
        "dosage_form": dosage_form,
        "product_kind": infer_product_kind(product_name, payload.get("product_kind")),
        "default_intake_unit": default_unit,
        "serving_quantity": _positive(payload.get("serving_quantity", 1), "serving_quantity"),
        "serving_unit": serving_unit,
        "package_size": _text(payload.get("package_size")),
        "formula_version": _text(payload.get("formula_version")),
        "label_version_date": label_date,
        "front_label_image_path": _text(payload.get("front_label_image_path")),
        "facts_label_image_path": _text(payload.get("facts_label_image_path")),
        "product_url": _text(payload.get("product_url")),
        "data_source": source,
        "primary_source_reference": source_reference,
        "primary_source_type": _text(payload.get("primary_source_type")),
        "verification_status": status,
        "user_confirmed": int(user_confirmed),
        "verified_at": verified_at,
        "valid_from": _text(payload.get("valid_from")),
        "valid_to": _text(payload.get("valid_to")),
        "supersedes_product_id": payload.get("supersedes_product_id"),
        "formula_hash": _text(payload.get("formula_hash")),
        "label_hash": _text(payload.get("label_hash")),
    }


def normalize_ingredient(payload: dict[str, Any]) -> dict[str, Any]:
    name = _text(payload.get("canonical_ingredient_name"))
    if not name:
        raise ValueError("INGREDIENT_NAME_REQUIRED")
    unit = str(payload.get("amount_unit") or "").lower()
    if unit not in INGREDIENT_UNITS:
        raise ValueError("INVALID_INGREDIENT_UNIT")
    serving_unit = normalize_unit(payload.get("serving_unit"))
    role = str(payload.get("ingredient_role") or "active")
    if role not in INGREDIENT_ROLES:
        raise ValueError("INVALID_INGREDIENT_ROLE")
    source_type = str(payload.get("source_type") or "manual_minimal")
    if source_type not in INGREDIENT_SOURCE_TYPES:
        raise ValueError("INVALID_INGREDIENT_SOURCE")
    confidence = str(payload.get("confidence_level") or "unknown")
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError("INVALID_INGREDIENT_CONFIDENCE")
    return {
        "canonical_ingredient_name": name,
        "display_name_zh": _text(payload.get("display_name_zh")),
        "display_name_en": _text(payload.get("display_name_en")),
        "amount_per_serving": _positive(payload.get("amount_per_serving"), "amount_per_serving"),
        "amount_unit": unit,
        "serving_quantity": _positive(payload.get("serving_quantity", 1), "ingredient_serving_quantity"),
        "serving_unit": serving_unit,
        "ingredient_role": role,
        "source_reference": _text(payload.get("source_reference")),
        "source_type": source_type,
        "confidence_level": confidence,
        "user_confirmed": int(bool(payload.get("user_confirmed"))),
    }


def normalize_intake(payload: dict[str, Any]) -> dict[str, Any]:
    product_id = payload.get("supplement_product_id")
    custom_product = _text(payload.get("custom_product_name"))
    if product_id in (None, "") and not custom_product:
        raise ValueError("PRODUCT_NAME_REQUIRED")
    return {
        "supplement_product_id": int(product_id) if product_id not in (None, "") else None,
        "custom_brand_name": _text(payload.get("custom_brand_name")),
        "custom_product_name": custom_product,
        "quantity": _positive(payload.get("quantity"), "supplement_quantity"),
        "unit": normalize_unit(payload.get("unit")),
        "taken_at": _text(payload.get("taken_at")) or "00:00:00",
        "source": str(payload.get("source") or "manual"),
        "notes": _text(payload.get("notes")),
    }
