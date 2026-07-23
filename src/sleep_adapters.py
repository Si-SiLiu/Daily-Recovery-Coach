"""Adapters from source-specific sleep projections to the canonical model."""

from __future__ import annotations

from typing import Any, Mapping

from .sleep_regularity import CanonicalSleepRecord, canonicalize_sleep_record


def polar_to_canonical(record: Mapping[str, Any]) -> CanonicalSleepRecord | None:
    """Adapt the existing Polar/domain projection without exposing raw fields."""
    value = dict(record)
    value.setdefault("source", "polar")
    return canonicalize_sleep_record(value)


class HealthKitSleepAdapter:
    """Reserved adapter boundary for future HealthKit/Apple Watch records."""

    source = "healthkit"

    def to_canonical(self, record: Mapping[str, Any]) -> CanonicalSleepRecord | None:
        value = dict(record)
        value.setdefault("source", self.source)
        return canonicalize_sleep_record(value)
