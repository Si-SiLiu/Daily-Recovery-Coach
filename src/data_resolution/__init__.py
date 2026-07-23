"""Canonical field resolution with explicit value provenance."""

from .config import DATA_RESOLUTION_VERSION, load_policy_config
from .models import ResolvedField, SourceCandidate
from .policies import ResolutionPolicyError, get_field_policy
from importlib import import_module


_RESOLVER_EXPORTS = {
    "resolve_activity_fields", "resolve_activity_session",
    "resolve_canonical_field", "resolve_field", "resolve_fields",
    "resolve_recovery_date", "resolve_recovery_fields",
    "resolve_sleep_date", "resolve_sleep_fields",
}


def __getattr__(name):
    if name in _RESOLVER_EXPORTS:
        return getattr(import_module(".resolver", __name__), name)
    raise AttributeError(name)

__all__ = [
    "DATA_RESOLUTION_VERSION",
    "SourceCandidate",
    "ResolvedField",
    "ResolutionPolicyError",
    "load_policy_config",
    "get_field_policy",
    "resolve_field",
    "resolve_canonical_field",
    "resolve_fields",
    "resolve_activity_fields",
    "resolve_activity_session",
    "resolve_sleep_fields",
    "resolve_sleep_date",
    "resolve_recovery_fields",
    "resolve_recovery_date",
]
