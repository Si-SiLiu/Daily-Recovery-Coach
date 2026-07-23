"""Value objects for source candidates and resolved fields."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SourceCandidate:
    value: Any
    record_id: int | str | None = None
    confirmed: bool = False

    @property
    def available(self) -> bool:
        return self.value is not None and self.value != ""


@dataclass(frozen=True)
class ResolvedField:
    field_name: str
    value: Any
    value_source: str
    source_record_id: int | str | None
    is_fallback: bool
    is_manual_override: bool
    resolution_reason: str
    resolved_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
