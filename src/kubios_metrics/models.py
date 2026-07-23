from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RawMeasurement:
    date: str
    source_type: str
    import_method: str
    source_priority: int
    measurement_time: str | None = None
    measurement_group_id: str | None = None
    reviewed: bool = False
    selected_as_primary: bool = False
    selection_reason: str | None = None
    source_file_sha256: str | None = None
    parser_version: str | None = None
    ocr_confidence: float | None = None
    values: dict[str, Any] | None = None
    raw_json: dict[str, Any] | None = None

    def to_dict(self):
        data = asdict(self)
        data.update(data.pop("values") or {})
        return data


@dataclass(frozen=True)
class NormalizedMeasurement:
    date: str
    source_raw_table: str
    source_raw_id: int
    source_type: str
    selection_reason: str
    source_priority: int
    core_data_completeness: float
    normalization_version: str
    measurement_time: str | None = None
    measurement_group_id: str | None = None
    selected_as_primary: bool = True
    values: dict[str, Any] | None = None

    def to_dict(self):
        data = asdict(self)
        data.update(data.pop("values") or {})
        return data
