"""Abstract marketplace interface."""

from __future__ import annotations

import abc
from collections.abc import Iterable

from ..models import Product


class Marketplace(abc.ABC):
    """A source of product offers.

    The same class is used for both *source* (buy) and *target* (sell) markets;
    the scanner decides the role. Implementations only need to know how to
    search/list products and return :class:`Product` objects.
    """

    name: str = "base"

    @abc.abstractmethod
    def search(self, query: str, *, limit: int = 50) -> list[Product]:
        """Return products matching a free-text query."""

    def fetch_catalog(self, *, limit: int = 100) -> list[Product]:
        """Return a sample/browse catalog (default: empty)."""
        return []

    def get_by_sku(self, sku: str) -> Product | None:
        """Best-effort lookup by SKU/UPC. Default: linear search of catalog."""
        for p in self.fetch_catalog():
            if p.sku == sku:
                return p
        return None

    def iter_categories(self) -> Iterable[str]:
        return []
