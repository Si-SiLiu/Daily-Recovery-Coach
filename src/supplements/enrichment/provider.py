"""Abstract provider surface; implementations require existing approval gate."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderBlockedError(RuntimeError):
    pass


class SupplementEnrichmentProvider(ABC):
    approved = False

    @abstractmethod
    def search_products(self, brand_name, product_name, barcode=None, region=None):
        raise NotImplementedError

    @abstractmethod
    def fetch_product_details(self, candidate_id):
        raise NotImplementedError
