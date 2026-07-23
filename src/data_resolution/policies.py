"""Canonical-field policy lookup; no broad cross-domain source ranking."""

from __future__ import annotations

from typing import Any

from .config import load_policy_config


class ResolutionPolicyError(ValueError):
    """Raised when a canonical field has no approved source policy."""


def get_field_policy(
    domain: str,
    field_name: str,
    policy_config: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    config = policy_config or load_policy_config()
    domain_config = config.get("domains", {}).get(domain)
    if not isinstance(domain_config, dict):
        raise ResolutionPolicyError(f"UNKNOWN_RESOLUTION_DOMAIN:{domain}")
    field_policy = domain_config.get("fields", {}).get(field_name)
    policy = field_policy if field_policy is not None else domain_config.get("default")
    if not isinstance(policy, list) or not policy:
        raise ResolutionPolicyError(f"MISSING_FIELD_POLICY:{domain}.{field_name}")
    return tuple(str(source) for source in policy)
