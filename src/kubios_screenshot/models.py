from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TextBlock:
    text: str
    confidence: float
    bounding_box: dict[str, float] = field(default_factory=dict)
    candidates: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class OCRResult:
    engine: str
    engine_version: str
    image_size: dict[str, int]
    text_blocks: list[TextBlock]
    raw_text: str
    processing_warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ParsedField:
    value: Any
    confidence: float
    source_text: str
    unit: str | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    candidates_consistent: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ParseResult:
    fields: dict[str, ParsedField]
    missing_required_fields: list[str]
    warnings: list[str]
    parser_version: str
    overall_confidence: float
    review_required: bool = True

    def to_dict(self):
        return {
            "fields": {name: value.to_dict() for name, value in self.fields.items()},
            "missing_required_fields": list(self.missing_required_fields),
            "warnings": list(self.warnings),
            "parser_version": self.parser_version,
            "overall_confidence": self.overall_confidence,
            "review_required": self.review_required,
        }


@dataclass(frozen=True)
class StoredImage:
    sha256: str
    original_relative_path: str
    processed_relative_path: str
    duplicate: bool = False


@dataclass(frozen=True)
class ImportResult:
    success: bool
    status: str
    raw_record_id: int | None = None
    audit_id: int | None = None
    conflict: dict[str, Any] | None = None
    downstream: dict[str, Any] = field(default_factory=dict)
