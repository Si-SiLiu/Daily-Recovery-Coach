"""Data-only enrichment candidate models."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProductCandidate:
    candidate_id: str
    brand_name: str | None
    product_name: str
    product_variant: str | None
    barcode: str | None
    dosage_form: str | None
    serving_quantity: float | None
    serving_unit: str | None
    ingredient_summary: tuple[dict, ...]
    source_name: str
    source_reference: str
    source_type: str
    confidence: float | None
    retrieved_at: str


@dataclass(frozen=True)
class ProductEnrichmentResult:
    candidate: ProductCandidate
    ingredients: tuple[dict, ...] = field(default_factory=tuple)
    conflicts: tuple[dict, ...] = field(default_factory=tuple)
    requires_user_confirmation: bool = True
