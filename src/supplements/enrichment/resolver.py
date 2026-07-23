"""Gate-enforced enrichment resolver with no cloud implementation enabled."""

from __future__ import annotations

from .provider import ProviderBlockedError, SupplementEnrichmentProvider


def enrichment_runtime_status(provider=None) -> str:
    return "provider_approved" if provider is not None and provider.approved else "provider_blocked"


def search_products(brand_name, product_name, barcode=None, region=None, provider=None):
    if provider is None or not isinstance(provider, SupplementEnrichmentProvider) or not provider.approved:
        raise ProviderBlockedError("SUPPLEMENT_ENRICHMENT_PROVIDER_BLOCKED")
    # A provider may return candidates only. Persisting or confirming them is a
    # separate explicit user action in the catalog service/UI.
    return provider.search_products(brand_name, product_name, barcode=barcode, region=region)
