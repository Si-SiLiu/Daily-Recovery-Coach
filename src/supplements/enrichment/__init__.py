"""Provider-agnostic candidate enrichment contracts; runtime remains gated."""

from .models import ProductCandidate, ProductEnrichmentResult
from .provider import ProviderBlockedError, SupplementEnrichmentProvider
from .resolver import enrichment_runtime_status, search_products

__all__ = [
    "ProductCandidate", "ProductEnrichmentResult", "ProviderBlockedError",
    "SupplementEnrichmentProvider", "enrichment_runtime_status", "search_products",
]
